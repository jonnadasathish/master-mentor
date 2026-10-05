"""Slice 4 behavior through the API: assessments, write effects, skill states, baseline, rebuild, export."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog, Base
from app.services.export_service import classified_tables
from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db

CONCEPT = {
    "kind": "CONCEPT_EXPLAIN",
    "source_key": "prompt:db-indexing-btree",
    "skills": [{"skill": "db.indexing", "outcome_points": 80}],
    "observed_at": "2026-10-03T06:00:00Z",
}


def skill(client: TestClient, key: str) -> dict[str, Any]:
    return get(client, f"/skills/{key}")["data"]


# ------------------------------------------------------------------------------- write envelope


def test_attempt_write_returns_effects_with_skill_deltas(activity_client: TestClient) -> None:
    body = post(activity_client, "/problem-attempts", SOLVED)
    assert set(body) == {"data", "meta", "effects"}
    assert body["data"]["outcome"] == "PASS"  # the stored record is still `data` (D-056)
    assert body["meta"]["as_of_date"] == "2026-10-04" and body["meta"]["ruleset_version"] == "v1"
    assert body["meta"]["run_id"] == body["effects"]["run_id"]
    deltas = {d["skill_key"]: d for d in body["effects"]["skill_deltas"]}
    # Two Sum (EASY) maps to arrays + hashing; a first clean untimed PASS on an EASY problem = L3 row,
    # but one row only qualifies L1 (needs 2 distinct sources for L2+).
    primary = next(iter(deltas.values()))
    assert primary["before"] is None
    assert primary["after"]["level"] == 1 and primary["after"]["confidence"] == "LOW"
    # A second write changes nothing for unrelated skills: deltas only list changed skills.
    again = post(activity_client, "/problem-attempts", {**SOLVED, "problem_id": 27, "outcome": "FAIL"})
    assert all(d["skill_key"] not in deltas or d["before"] for d in again["effects"]["skill_deltas"])


def test_skill_state_is_traceable_to_evidence(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    listing = get(activity_client, "/skills", component="dsa")
    assert listing["meta"]["run_id"] >= 1 and listing["meta"]["count"] == len(listing["data"])
    assessed = [s for s in listing["data"] if s["state"]["assessed"]]
    assert assessed, "the attempt must assess at least one dsa skill"
    mapped = get(activity_client, "/problems/1")["data"]["skills"][0]["skill"]  # Two Sum's primary skill
    assert mapped in {s["key"] for s in assessed}
    detail = skill(activity_client, mapped)
    assert detail["state"]["evidence_count"] == len([e for e in detail["evidence"] if e["is_scoring"]])
    assert any(e["considered"] for e in detail["evidence"])
    assert any(e["qualifying"] for e in detail["evidence"])
    row = detail["evidence"][0]
    assert (row["source_type"], row["rule"]) == ("ATTEMPT", "MAPPED")


def test_unassessed_skill_has_no_score(activity_client: TestClient) -> None:
    detail = skill(activity_client, "db.indexing")
    assert detail["state"] == {**detail["state"], "score": None, "confidence": "NONE", "label": "UNASSESSED"}
    assert detail["evidence"] == []


def test_unknown_skill_is_404(activity_client: TestClient) -> None:
    assert get(activity_client, "/skills/no.such", status=404)["error"]["code"] == "NOT_FOUND"


# ------------------------------------------------------------------------------- assessments


def test_assessment_is_stored_and_scored(activity_client: TestClient) -> None:
    body = post(activity_client, "/assessments", CONCEPT)
    data = body["data"]
    assert (data["kind"], data["observed_on"], data["is_current"]) == ("CONCEPT_EXPLAIN", "2026-10-03", True)
    assert data["skills"] == [
        {"skill": "db.indexing", "outcome_points": 80, "mapping_weight_bp": 10000, "is_pattern_target": False}
    ]
    (delta,) = body["effects"]["skill_deltas"]
    assert delta["skill_key"] == "db.indexing"
    # One L3 row at 80 points qualifies only L1 (L2+ need two distinct sources): 10 + 20 x 80/100 = 26.
    assert delta["after"] == {"score": 26, "effective": 11, "level": 1, "confidence": "LOW"}
    assert delta["before"] is None


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"familiarity": "SOME"}, "only allowed on SELF_ASSESSMENT"),
        ({"skills": [{"skill": "no.such", "outcome_points": 50}]}, "unknown or inactive skill"),
        ({"skills": [{"skill": "db.indexing"}]}, "outcome_points required"),
        ({"kind": "STORY_REHEARSAL"}, "cannot observe"),
        ({"timed": True}, "required when timed is true"),
        ({"observed_at": "2026-10-05T06:00:00Z"}, "cannot be in the future"),
        ({"study_minutes": 30}, "only allowed on STUDY_SESSION"),
    ],
)
def test_assessment_validation(activity_client: TestClient, override: dict[str, Any], message: str) -> None:
    body = post(activity_client, "/assessments", {**CONCEPT, **override}, status=422)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(message in e["msg"] for e in body["error"]["details"]["errors"]), body


def test_unknown_assessment_field_is_rejected(activity_client: TestClient) -> None:
    post(activity_client, "/assessments", {**CONCEPT, "score": 90}, status=422)


def test_duplicate_client_request_id_is_409(activity_client: TestClient) -> None:
    first = post(activity_client, "/assessments", {**CONCEPT, "client_request_id": "req-assess-1"})
    dup = post(activity_client, "/assessments", {**CONCEPT, "client_request_id": "req-assess-1"}, status=409)
    assert dup["error"]["details"] == {"assessment_id": first["data"]["id"]}


def test_correction_appends_and_recalculates(activity_client: TestClient, catalog_engine: Engine) -> None:
    original = post(activity_client, "/assessments", CONCEPT)["data"]
    corrected = post(
        activity_client,
        f"/assessments/{original['id']}/corrections",
        {**CONCEPT, "skills": [{"skill": "db.indexing", "outcome_points": 20}]},
    )
    assert corrected["data"]["supersedes_id"] == original["id"]
    # 20 points qualify nothing: L0 band, quality 20 -> 0 + 10 x 20/100 = 2.
    assert corrected["effects"]["skill_deltas"][0]["after"] == {
        "score": 2,
        "effective": 0,
        "level": 0,
        "confidence": "LOW",
    }
    old = get(activity_client, f"/assessments/{original['id']}")["data"]
    assert (old["is_current"], old["superseded_by_id"]) == (False, corrected["data"]["id"])
    assert old["skills"][0]["outcome_points"] == 80  # history unchanged
    again = post(activity_client, f"/assessments/{original['id']}/corrections", CONCEPT, status=409)
    assert again["error"]["details"]["latest_assessment_id"] == corrected["data"]["id"]
    current = get(activity_client, "/assessments")["data"]
    assert [a["id"] for a in current] == [corrected["data"]["id"]]
    with sessionmaker(bind=catalog_engine)() as session:
        actions = session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "assessment")).all()
    assert sorted(actions) == ["CORRECT_ASSESSMENT", "CREATE_ASSESSMENT"]


def test_self_assessment_never_raises_a_score(activity_client: TestClient) -> None:
    post(
        activity_client,
        "/assessments/self-assessment-sweep",
        {"entries": [{"skill": "db.indexing", "familiarity": "SOLID"}]},
    )
    state = skill(activity_client, "db.indexing")["state"]
    assert (state["score"], state["assessed"]) == (None, False)


# ------------------------------------------------------------------------------- baseline / cold start


def test_sweep_declares_unknown_and_completes_battery_item(activity_client: TestClient) -> None:
    before = get(activity_client, "/baseline")["data"]
    assert (before["battery_complete"], before["next_item"], before["calibration_mode"]) == (
        False,
        "M0-B01",
        True,
    )
    assert before["battery_total"] == 12 and before["assessed_required"] == 0
    body = post(
        activity_client,
        "/assessments/self-assessment-sweep",
        {
            "entries": [
                {"skill": "db.indexing", "familiarity": "NONE"},
                {"skill": "graph.traversal", "familiarity": "SOME"},
            ],
            "client_request_id": "sweep-0001",
        },
    )
    assert body["meta"]["count"] == 2
    assert {a["battery_item_key"] for a in body["data"]} == {"M0-B01"}
    unknown = skill(activity_client, "db.indexing")["state"]
    assert (unknown["score"], unknown["level"], unknown["confidence"], unknown["declared_unknown"]) == (
        0,
        0,
        "LOW",
        True,
    )
    assert skill(activity_client, "graph.traversal")["state"]["assessed"] is False
    after = get(activity_client, "/baseline")["data"]
    assert after["items"][0]["complete"] is True and after["next_item"] == "M0-B02"
    assert after["assessed_required"] == 1 and after["calibration_mode"] is True  # no premature exit
    post(
        activity_client,
        "/assessments/self-assessment-sweep",
        {"entries": [{"skill": "db.indexing", "familiarity": "NONE"}], "client_request_id": "sweep-0001"},
        status=409,
    )


def test_attempt_with_battery_key_completes_that_item(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", {**SOLVED, "battery_item_key": "M0-B02", "mode": "BASELINE"})
    items = {i["key"]: i["complete"] for i in get(activity_client, "/baseline")["data"]["items"]}
    assert items["M0-B02"] is True and items["M0-B01"] is False


# ------------------------------------------------------------------------------- rebuild / replay


def derived_snapshot(engine: Engine) -> dict[str, list[tuple[Any, ...]]]:
    with engine.connect() as connection:
        evidence = connection.execute(
            text(
                "SELECT source_type, source_id, skill_id, rule, level, outcome_points, is_scoring, "
                "observed_on FROM evidence ORDER BY source_type, source_id, skill_id"
            )
        ).all()
        states = connection.execute(
            text(
                "SELECT skill_id, score, level, quality, confidence, effective_score, peak_score, "
                "evidence_count, label, considered_evidence_json FROM skill_states ORDER BY skill_id"
            )
        ).all()
        hashes = connection.execute(text("SELECT input_hash FROM mentor_runs ORDER BY id DESC LIMIT 1")).all()
    return {"evidence": [tuple(r) for r in evidence], "states": [tuple(r) for r in states], "hash": hashes}


def test_rebuild_reproduces_derived_state_exactly(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    post(
        activity_client,
        "/problem-attempts",
        {**SOLVED, "problem_id": 27, "outcome": "FAIL", "mistakes": ["WRONG_PATTERN"]},
    )
    post(activity_client, "/assessments", CONCEPT)
    first = derived_snapshot(catalog_engine)
    for _ in range(2):
        result = post(activity_client, "/admin/rebuild", {}, status=200)["data"]
        assert result["runs"] >= 1 and result["evidence_rows"] == len(first["evidence"])
        assert derived_snapshot(catalog_engine) == first
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(AuditLog.action).where(AuditLog.action == "REBUILD_DERIVED")) is not None


# ------------------------------------------------------------------------------- export


def test_json_export_contains_raw_data_and_no_derived_tables(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    post(activity_client, "/assessments", CONCEPT)
    response = activity_client.get("/api/v1/export/json")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    doc = json.loads(response.content)
    assert (doc["format"], doc["format_version"], doc["seed_version"]) == (
        "master-mentor-export",
        2,  # v2: id_maps for import (D-075)
        "seed-v1",
    )
    assert doc["counts"]["problem_attempts"] == 1 and doc["counts"]["assessments"] == 1
    assert doc["counts"]["problems"] == 0  # catalog problems are reproducible from seed/
    assert not {"evidence", "skill_states", "skill_daily_snapshots"} & set(doc["tables"])
    assert doc["tables"]["problem_attempts"][0]["attempted_at"] == "2026-10-04T12:00:00Z"


def test_csv_export_is_a_zip_with_one_file_per_table(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    response = activity_client.get("/api/v1/export/csv")
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "problem_attempts.csv", "assessments.csv", "audit_log.csv"} <= names
        lines = archive.read("problem_attempts.csv").decode().splitlines()
    assert lines[0].startswith("id,problem_id,attempted_on") and len(lines) == 2


def test_every_table_is_classified_for_export() -> None:
    assert set(Base.metadata.tables) == classified_tables()
