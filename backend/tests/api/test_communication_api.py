"""Communication track through the API (D-087): speaking practice evidence, validation, self-report,
append-only history and Communication Readiness. Everything goes through the existing assessment path."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Assessment, AssessmentSkill, SpeakingPractice
from tests.api.test_activity_api import get, post

pytestmark = pytest.mark.db
PRACTICE = "comm.speak_1m.practice"
TIMED = "comm.speak_1m.timed"
SKILL = "comm.speak_1m"
GOOD = (
    "First, I will explain the bug I fixed last week. The root cause was a missing index on orders. "
    "Because of that, the checkout query scanned every row and it was slow. Then I added the index and I "
    "measured the result. Finally the latency dropped from two seconds to forty milliseconds, for example "
    "during the morning peak, and I wrote a short note for the team about the rollback plan."
)
FULL = {f"p{i}": 2 for i in range(5)}


def speak(client: TestClient, key: str = PRACTICE, status: int = 201, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "ratings": FULL,
        "speech": {"source": "BROWSER", "transcript": GOOD, "duration_seconds": 55},
        **overrides,
    }
    response = client.post(f"/api/v1/learning/content/{key}/complete", json=body)
    assert response.status_code == status, response.text
    return response.json()


def skill(client: TestClient, key: str) -> dict[str, Any]:
    return get(client, f"/skills/{key}")["data"]


def evidence_levels(client: TestClient, key: str) -> set[tuple[str, int]]:
    return {(e["kind"], e["level"]) for e in skill(client, key)["evidence"]}


def practices(engine: Engine) -> list[SpeakingPractice]:
    with sessionmaker(bind=engine)() as session:
        rows = list(session.scalars(select(SpeakingPractice).order_by(SpeakingPractice.id)))
        session.expunge_all()
        return rows


# ------------------------------------------------------------------------------------------- evidence


def test_browser_practice_records_one_concept_explain_on_the_communication_skill_only(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    out = speak(activity_client)["data"]
    observation = out["observation"]
    assert observation["kind"] == "CONCEPT_EXPLAIN" and observation["reference_used"] is False
    assert [s["skill"] for s in observation["skills"]] == [SKILL]  # nothing else is credited
    assert out["speaking"]["source"] == "BROWSER" and out["speaking"]["metrics_version"] == "speak-v1"
    assert out["speaking"]["word_count"] > 50 and "criteria" in out["speaking"]
    assert ("CONCEPT_EXPLAIN", 3) in evidence_levels(activity_client, SKILL)  # independent practice = L3
    (row,) = practices(catalog_engine)
    assert (row.source, row.assessment_id) == ("BROWSER", observation["id"])
    assert row.transcript == GOOD and row.metrics_version == "speak-v1" and row.duration_seconds == 55
    assert row.word_count == out["speaking"]["word_count"] and "audio" not in row.metrics_json
    assert evidence_levels(activity_client, "dsa.complexity_analysis") == set()  # no other skill changed


def test_manual_practice_is_weaker_evidence_and_never_looks_measured(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    out = speak(activity_client, speech={"source": "MANUAL", "duration_seconds": 40})["data"]
    assert out["observation"]["reference_used"] is True  # recorded as supported practice
    assert out["speaking"]["source"] == "MANUAL" and out["speaking"]["criteria"] == {}
    assert out["speaking"]["word_count"] == 0 and "weaker evidence" in out["speaking"]["evidence_note"]
    levels = evidence_levels(activity_client, SKILL)
    assert ("CONCEPT_EXPLAIN", 2) in levels and ("CONCEPT_EXPLAIN", 3) not in levels
    (row,) = practices(catalog_engine)
    assert (row.source, row.transcript, row.word_count) == ("MANUAL", None, 0)


def test_timed_browser_speech_is_stronger_only_within_the_limit(activity_client: TestClient) -> None:
    within = speak(
        activity_client,
        TIMED,
        timed=True,
        time_seconds=999,
        speech={"source": "BROWSER", "transcript": GOOD, "duration_seconds": 100},
    )["data"]["observation"]
    assert (within["timed"], within["time_seconds"], within["time_limit_seconds"]) == (True, 100, 120)
    assert ("CONCEPT_EXPLAIN", 4) in evidence_levels(
        activity_client, SKILL
    )  # the server used its own duration
    over = speak(
        activity_client,
        TIMED,
        timed=True,
        speech={"source": "BROWSER", "transcript": GOOD, "duration_seconds": 150},
    )["data"]["observation"]
    assert over["time_seconds"] == 150 and over["time_limit_seconds"] == 120  # over the limit: not within


def test_manual_practice_cannot_claim_a_timed_result(activity_client: TestClient) -> None:
    out = speak(
        activity_client,
        TIMED,
        timed=True,
        time_seconds=30,
        speech={"source": "MANUAL", "duration_seconds": 30},
    )["data"]["observation"]
    assert out["timed"] is False and out["time_seconds"] is None
    assert ("CONCEPT_EXPLAIN", 4) not in evidence_levels(activity_client, SKILL)


def test_self_report_never_raises_a_communication_skill(activity_client: TestClient) -> None:
    before = skill(activity_client, SKILL)["state"]
    post(
        activity_client,
        "/assessments/self-assessment-sweep",
        {"entries": [{"skill": SKILL, "familiarity": "SOLID"}]},
    )
    after = skill(activity_client, SKILL)["state"]
    assert (after["score"], after["assessed"], after["confidence"]) == (None, False, "NONE")
    assert before["score"] is None
    ready = get(activity_client, "/communication/readiness")["data"]
    fluency = next(a for a in ready["areas"] if a["key"] == "comm.fluency")
    assert fluency["status"] == "NOT_STARTED" and fluency["measured_rows"] == 0
    assert (
        fluency["summary"] == "Self-reported only, not measured yet." and fluency["self_reported_only"] == 1
    )


def test_speech_is_checked_on_the_server(activity_client: TestClient) -> None:
    def refused(speech: dict[str, Any], key: str = PRACTICE, message: str = "") -> None:
        body = speak(activity_client, key, status=422, speech=speech)
        assert message in body["error"]["message"] or message in str(body)

    refused({"source": "BROWSER", "duration_seconds": 30}, message="at least 5 words")
    refused(
        {"source": "BROWSER", "transcript": "too few words", "duration_seconds": 30}, message="at least 5"
    )
    refused({"source": "MANUAL", "transcript": GOOD, "duration_seconds": 30}, message="no transcript")
    refused(
        {"source": "BROWSER", "transcript": GOOD, "duration_seconds": 3}, message="too long for the recorded"
    )
    refused({"source": "BROWSER", "transcript": GOOD, "duration_seconds": 0}, message="duration")
    refused({"source": "BROWSER", "transcript": GOOD, "duration_seconds": 30, "word_count": 99}, message="")
    refused({"source": "AUDIO", "transcript": GOOD, "duration_seconds": 30}, message="")
    refused({"source": "BROWSER", "transcript": "x " * 5000, "duration_seconds": 30}, message="")
    check = activity_client.post(
        "/api/v1/learning/content/dsa.complexity.check/complete",
        json={"answers": {}, "speech": {"source": "MANUAL", "duration_seconds": 5}},
    )
    assert check.status_code == 422  # only an interview question can be a speaking practice
    assert evidence_levels(activity_client, SKILL) == set()  # nothing was recorded


def test_repeated_submission_is_refused_and_history_is_append_only(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    first = speak(activity_client, client_request_id="speak-req-0001")["data"]
    again = speak(activity_client, status=409, client_request_id="speak-req-0001")
    assert "already recorded" in str(again)
    rows = practices(catalog_engine)
    assert len(rows) == 1 and rows[0].assessment_id == first["observation"]["id"]
    second = speak(activity_client, client_request_id="speak-req-0002")["data"]
    after = practices(catalog_engine)
    assert [r.id for r in after] == [rows[0].id, after[1].id] and after[1].assessment_id != rows[
        0
    ].assessment_id
    assert after[0].transcript == rows[0].transcript and after[0].created_at == rows[0].created_at
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(func.count()).select_from(Assessment)) == 2
        credited = session.scalars(
            select(AssessmentSkill.assessment_id).where(
                AssessmentSkill.assessment_id == second["observation"]["id"]
            )
        ).all()
    assert len(credited) == 1


def test_a_failed_speaking_write_leaves_no_orphan_assessment(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    speak(
        activity_client,
        status=422,
        speech={"source": "BROWSER", "transcript": "short", "duration_seconds": 9},
    )
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(func.count()).select_from(Assessment)) == 0
        assert session.scalar(select(func.count()).select_from(SpeakingPractice)) == 0


def test_communication_practice_does_not_move_overall_readiness(activity_client: TestClient) -> None:
    before = get(activity_client, "/readiness")["data"]
    speak(activity_client)
    after = get(activity_client, "/readiness")["data"]
    assert after["components"] == before["components"]  # every technical component score
    assert after["weighted_score"] == before["weighted_score"]
    assert after["gates"] == before["gates"]  # including G8: spoken practice cannot satisfy technical recency
    assert (after["state"], after["blockers"], after["all_failing"]) == (
        before["state"],
        before["blockers"],
        before["all_failing"],
    )
    required = get(activity_client, "/catalog/role-profile")["data"]["required_skill_count"]
    assert required == 123


# ------------------------------------------------------------------------------------------ read models


def test_preview_measures_without_storing(activity_client: TestClient, catalog_engine: Engine) -> None:
    out = post(
        activity_client,
        "/communication/preview",
        {"content_key": PRACTICE, "transcript": GOOD, "duration_seconds": 55},
        status=200,
    )["data"]
    assert out["content_key"] == PRACTICE and out["speaking"]["source"] == "BROWSER"
    assert out["speaking"]["criteria"]["structure"] in (0, 1, 2)
    assert practices(catalog_engine) == [] and evidence_levels(activity_client, SKILL) == set()
    bad = activity_client.post(
        "/api/v1/communication/preview",
        json={"content_key": "nope.nope", "transcript": GOOD, "duration_seconds": 5},
    )
    assert bad.status_code == 404


def test_communication_readiness_has_six_areas_and_separates_measured_from_manual(
    activity_client: TestClient,
) -> None:
    ready = get(activity_client, "/communication/readiness")["data"]
    assert [a["key"] for a in ready["areas"]] == [
        "comm.spoken_foundation",
        "comm.fluency",
        "comm.workplace",
        "comm.technical_explanation",
        "comm.writing",
        "comm.interview",
    ]
    assert all(a["status"] == "NOT_STARTED" and a["summary"] == "Not measured yet." for a in ready["areas"])
    assert "not part of Overall Readiness" in ready["note"]
    speak(activity_client)
    speak(activity_client, speech={"source": "MANUAL", "duration_seconds": 20})
    fluency = next(
        a
        for a in get(activity_client, "/communication/readiness")["data"]["areas"]
        if a["key"] == "comm.fluency"
    )
    assert (fluency["measured_rows"], fluency["manual_rows"]) == (1, 1)
    assert "1 measured speaking practice and 1 manual self-review" in fluency["summary"]
    assert fluency["skills_with_evidence"] == 1 and fluency["status"] != "NOT_STARTED"


def test_communication_revision_item_comes_from_real_practice(activity_client: TestClient) -> None:
    def mine() -> list[dict[str, Any]]:
        items = get(activity_client, "/revisions")["data"]["items"]
        return [i for i in items if i["skill"] == SKILL]

    assert mine() == []
    speak(activity_client)
    assert [(i["item_key"], i["item_type"]) for i in mine()] == [(f"CONCEPT:{SKILL}", "CONCEPT")]


def revision_item(client: TestClient) -> dict[str, Any] | None:
    items = get(client, "/revisions")["data"]["items"]
    return next((i for i in items if i["skill"] == SKILL), None)


def test_a_second_practice_does_not_duplicate_the_revision_item(activity_client: TestClient) -> None:
    speak(activity_client)
    speak(
        activity_client,
        TIMED,
        timed=True,
        speech={"source": "BROWSER", "transcript": GOOD, "duration_seconds": 90},
    )
    items = [i for i in get(activity_client, "/revisions")["data"]["items"] if i["skill"] == SKILL]
    assert [i["item_key"] for i in items] == [f"CONCEPT:{SKILL}"]  # one item per communication skill


def test_a_communication_review_moves_the_item_and_never_the_technical_state(
    activity_client: TestClient,
) -> None:
    speak(activity_client)
    before = revision_item(activity_client)
    assert before is not None and before["item_type"] == "CONCEPT"
    technical = get(activity_client, "/readiness")["data"]
    tech_state = get(activity_client, "/skills/dsa.complexity_analysis")["data"]["state"]
    review = post(
        activity_client,
        "/assessments",
        {
            "kind": "RECALL_QUIZ",
            "source_key": "revision:comm.speak_1m",
            "revision_item_key": before["item_key"],
            "skills": [{"skill": SKILL, "outcome_points": 95}],
        },
    )
    assert any(c["item_key"] == before["item_key"] for c in review["effects"]["revision_changes"])
    after = revision_item(activity_client)
    assert after is not None and after["interval_index"] > before["interval_index"]
    assert after["last_reviewed_on"] is not None
    now = get(activity_client, "/readiness")["data"]
    assert (now["components"], now["weighted_score"], now["gates"]) == (
        technical["components"],
        technical["weighted_score"],
        technical["gates"],
    )
    assert get(activity_client, "/skills/dsa.complexity_analysis")["data"]["state"] == tech_state


def test_a_failed_communication_review_brings_it_back_without_touching_technical_work(
    activity_client: TestClient,
) -> None:
    speak(activity_client)
    item = revision_item(activity_client)
    assert item is not None
    post(
        activity_client,
        "/assessments",
        {
            "kind": "RECALL_QUIZ",
            "source_key": "revision:comm.speak_1m",
            "revision_item_key": item["item_key"],
            "skills": [{"skill": SKILL, "outcome_points": 20}],
        },
    )
    failed = revision_item(activity_client)
    assert failed is not None and (failed["interval_index"], failed["lapses"]) == (0, 1)
    assert failed["needs_reinforcement"] is True


def test_history_lists_counts_only_newest_first_and_never_the_transcript(activity_client: TestClient) -> None:
    assert get(activity_client, "/communication/history")["data"]["rows"] == []
    speak(
        activity_client,
        speech={"source": "BROWSER", "transcript": GOOD, "duration_seconds": 55, "reflection": "slower"},
    )
    speak(activity_client, speech={"source": "MANUAL", "duration_seconds": 20})
    data = get(activity_client, "/communication/history")["data"]
    rows = data["rows"]
    assert [r["source"] for r in rows] == ["MANUAL", "BROWSER"]  # newest first
    assert all(r["skill"] == SKILL and r["content_key"] == PRACTICE for r in rows)
    assert rows[1]["reflection"] == "slower" and rows[1]["filler_per_100_words"] is not None
    assert rows[0]["filler_per_100_words"] is None and rows[0]["word_count"] == 0  # nothing was measured
    assert "transcript" not in rows[0] and GOOD not in str(data) and "never stores audio" in data["note"]
    assert get(activity_client, "/communication/history", limit=1)["meta"]["count"] == 1


def test_the_starting_profile_self_report_is_shown_as_context_and_never_as_evidence(
    activity_client: TestClient,
) -> None:
    put = activity_client.put("/api/v1/profile", json={"self_report": {"weaknesses": ["comm.fluency"]}})
    assert put.status_code == 200, put.text
    ready = get(activity_client, "/communication/readiness")["data"]
    fluency = next(a for a in ready["areas"] if a["key"] == "comm.fluency")
    assert fluency["self_report"] == "Self-reported: weak (context only, not measured)"
    assert fluency["status"] == "NOT_STARTED" and fluency["summary"] == "Not measured yet."
    assert fluency["skills_with_evidence"] == 0 and fluency["measured_rows"] == 0
    assert skill(activity_client, SKILL)["state"]["score"] is None
    speak(activity_client)
    after = next(
        a
        for a in get(activity_client, "/communication/readiness")["data"]["areas"]
        if a["key"] == "comm.fluency"
    )
    assert after["self_report"] == fluency["self_report"] and "measured speaking practice" in after["summary"]
    other = next(
        a
        for a in get(activity_client, "/communication/readiness")["data"]["areas"]
        if a["key"] == "comm.writing"
    )
    assert other["self_report"] is None


# ------------------------------------------------------------- no component-based leak into technical views


def test_communication_skills_are_not_listed_as_technical_round_skills_or_mock_prompts(
    activity_client: TestClient,
) -> None:
    kits = get(activity_client, "/learning/mock-kits")["data"]
    assert kits and all(not i["skills"][0].startswith("comm.") for k in kits for i in k["items"])
    coding_gaps = get(activity_client, "/gaps", component="coding")["data"]["gaps"]
    assert coding_gaps and not any(g["skill_key"].startswith("comm.") for g in coding_gaps)
    assert any(g["skill_key"].startswith("comm.") for g in get(activity_client, "/gaps")["data"]["gaps"])
    detail = get(activity_client, f"/skills/{SKILL}/learning")["data"]
    assert detail["why_it_matters"]["rounds"] == []  # "tested in DSA rounds" would be false
    rows = get(activity_client, "/learning/coverage")["data"]["rows"]
    assert next(r for r in rows if r["skill_key"] == SKILL)["mock_coverage"] == []
    assert next(r for r in rows if r["skill_key"] == "python.core_syntax")["mock_coverage"] != []
