"""Learning layer through the API (MASTER_SPEC_V3 Phase B vertical slice): one skill -> lesson ->
concept check -> completion -> evidence -> skill state; skill learning; sessions; curriculum; coverage."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog
from tests.api.test_activity_api import get, post

pytestmark = pytest.mark.db
CHECK = "dsa.complexity.check"
RIGHT = {"q1": [1], "q2": [2], "q3": [0, 1], "q4": [2], "q5": [1]}


def complete(client: TestClient, key: str, body: dict[str, Any], status: int = 201) -> dict[str, Any]:
    response = client.post(f"/api/v1/learning/content/{key}/complete", json=body)
    assert response.status_code == status, response.text
    return response.json()


def test_check_hides_answers_until_submitted(activity_client: TestClient) -> None:
    data = get(activity_client, f"/learning/content/{CHECK}")["data"]
    assert data["type"] == "concept_check" and data["tab"] == "test" and data["pass_points"] == 60
    for q in data["body"]["questions"]:
        assert not {"answer", "explanation"} & set(q)
        assert ("model_answer" in q) == (q["kind"] == "short")  # needed to self-grade a short answer
    assert data["topic"] == {
        "key": "dsa.method",
        "title": "Problem-solving method and complexity",
        "track": "dsa",
    }
    assert data["progress"] is None
    lesson = get(activity_client, "/learning/content/dsa.complexity.lesson")["data"]
    assert lesson["body"]["mental_model"] and lesson["pass_points"] is None
    assert activity_client.get("/api/v1/learning/content/nope.nothing").status_code == 404


def test_vertical_slice_lesson_check_evidence_skill_state(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    before = get(activity_client, "/skills/dsa.complexity_analysis")["data"]
    assert before["state"]["confidence"] == "NONE"

    lesson = complete(activity_client, "dsa.complexity.lesson", {"minutes": 18})
    assert lesson["data"]["observation"]["kind"] == "STUDY_SESSION"
    assert lesson["data"]["observation"]["source_key"] == "content:dsa.complexity.lesson"
    assert lesson["data"]["points"] is None and lesson["data"]["progress"]["completions"] == 1

    graded = complete(activity_client, CHECK, {"answers": RIGHT, "self_grades": {"q6": 2}})
    data = graded["data"]
    assert (data["points"], data["passed"]) == (100, True)
    assert data["observation"]["kind"] == "RECALL_QUIZ" and data["observation"]["notes_used"] is False
    assert [q["earned"] for q in data["questions"]] == [2, 2, 2, 2, 2, 2]
    assert data["questions"][0]["answer"] == [1] and data["questions"][0]["explanation"]
    deltas = {d["skill_key"]: d for d in graded["effects"]["skill_deltas"]}
    assert "dsa.complexity_analysis" in deltas

    after = get(activity_client, "/skills/dsa.complexity_analysis")["data"]
    assert after["state"]["confidence"] != "NONE" and after["state"]["score"] is not None
    levels = {(e["kind"], e["level"]) for e in after["evidence"]}
    assert ("RECALL_QUIZ", 1) in levels  # closed-book recall = L1 (EVIDENCE_MODEL §5.4), not more
    assert ("STUDY_SESSION", 0) in levels

    progress = get(activity_client, f"/learning/content/{CHECK}")["data"]["progress"]
    assert (progress["completions"], progress["best_points"], progress["passed"]) == (1, 100, True)
    with sessionmaker(bind=catalog_engine)() as session:
        actions = list(session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "assessment")))
        assert actions.count("CREATE_ASSESSMENT") == 2  # recorded through the ordinary assessment path


def test_failed_and_open_book_checks(activity_client: TestClient) -> None:
    failed = complete(activity_client, CHECK, {"answers": {"q1": [0]}})["data"]
    assert (failed["points"], failed["passed"]) == (0, False)
    open_book = complete(
        activity_client, CHECK, {"answers": RIGHT, "self_grades": {"q6": 2}, "notes_used": True}
    )
    assert open_book["data"]["observation"]["notes_used"] is True
    progress = get(activity_client, f"/learning/content/{CHECK}")["data"]["progress"]
    assert (progress["completions"], progress["last_points"], progress["best_points"]) == (2, 100, 100)
    skill = get(activity_client, "/skills/dsa.complexity_analysis")["data"]
    assert {(e["kind"], e["level"]) for e in skill["evidence"]} >= {
        ("RECALL_QUIZ", 0)
    }  # open book proves nothing


def test_rubric_exercise_timed_within_limit(activity_client: TestClient) -> None:
    body = {
        "ratings": {"correct": 2, "linear": 2, "no_self_pair": 2, "complexity_stated": 2},
        "followups": {"0": 2},
        "timed": True,
        "time_seconds": 700,
    }
    out = complete(activity_client, "dsa.complexity.exercise", body)["data"]
    assert (out["points"], out["followup_points"]) == (100, 100)
    obs = out["observation"]
    assert (obs["kind"], obs["timed"], obs["time_limit_seconds"], obs["time_seconds"]) == (
        "CODE_EXERCISE",
        True,
        900,
        700,
    )
    levels = {e["level"] for e in get(activity_client, "/skills/dsa.complexity_analysis")["data"]["evidence"]}
    assert 5 in levels  # timed + follow-up >= 70 = L5 by the existing practice ladder


def test_problem_content_and_bad_submissions_are_refused(activity_client: TestClient) -> None:
    complete(activity_client, "dsa.binary_search.guided", {}, status=409)
    complete(activity_client, CHECK, {"ratings": {"x": 3}}, status=422)
    complete(activity_client, CHECK, {"unknown": 1}, status=422)


def test_skill_learning_read_model_cases(activity_client: TestClient) -> None:
    concept = get(activity_client, "/skills/dsa.complexity_analysis/learning")["data"]
    assert concept["practice"]["case"] == "CONCEPT" and concept["practice"]["direct"] == []
    assert [c["type"] for c in concept["tabs"]["learn"]][:2] == ["lesson", "worked_example"]
    assert {c["key"] for c in concept["tabs"]["test"]} >= {CHECK, "dsa.complexity.compare"}
    assert concept["tabs"]["revision"][0]["key"] == "dsa.complexity.cards"
    assert (
        concept["why_it_matters"]["tier_label"] == "CRITICAL" and "DSA" in concept["why_it_matters"]["rounds"]
    )
    # The mentor's own focus decides the stage: an unmeasured skill is diagnosed first (MENTOR_ENGINE)
    assert concept["next_action"]["kind"] == "START_SESSION" and concept["next_action"]["stage"] == "DIAGNOSE"
    assert concept["next_action"]["reason"] == "GAP_FOCUS"
    assert concept["next_action"]["steps"][0]["content_key"] == CHECK
    assert concept["coverage_state"] == "FULL"

    direct = get(activity_client, "/skills/binary_search.basic/learning")["data"]
    assert direct["practice"]["case"] == "DIRECT"
    first = direct["practice"]["direct"][0]
    assert (first["id"], first["practice_state"]) == (15, "not_started")
    assert first["url"] == "https://leetcode.com/problems/binary-search/"
    relations = {r["relation"] for r in direct["related_skills"]}
    assert "DEPENDENT" in relations and "SAME_TOPIC" in relations
    assert activity_client.get("/api/v1/skills/ghost.skill/learning").status_code == 404


def test_session_start_resume_complete_and_repeat(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    started = post(
        activity_client, "/learning/sessions", {"skill": "dsa.complexity_analysis", "stage": "LEARN"}
    )["data"]
    assert started["status"] == "ACTIVE" and started["stage"] == "LEARN" and started["next_position"] == 1
    kinds = [(s["kind"], s["content_key"]) for s in started["steps"]]
    assert kinds[0] == ("CONTENT", "dsa.complexity.lesson") and kinds[-1] == ("REFLECTION", None)
    assert started["before"] == {"score": None, "level": None}
    resumed = post(activity_client, "/learning/sessions", {"skill": "dsa.complexity_analysis"})["data"]
    assert resumed["id"] == started["id"]  # one active session per skill: starting again resumes it

    sid = started["id"]
    for step in started["steps"]:
        pos = step["position"]
        if step["content_type"] == "concept_check":
            body = {"completion": {"answers": RIGHT, "self_grades": {"q6": 2}}}
        elif step["kind"] == "REFLECTION":
            body = {"reflection": "Count operations, not loops."}
        elif step["content_type"] in ("lesson", "worked_example", "visual_explanation"):
            body = {"completion": {}}
        else:
            skipped = post(activity_client, f"/learning/sessions/{sid}/steps/{pos}/skip", {}, status=200)[
                "data"
            ]
            assert skipped["steps"][pos - 1]["status"] == "SKIPPED"
            continue
        response = activity_client.post(f"/api/v1/learning/sessions/{sid}/steps/{pos}/complete", json=body)
        assert response.status_code == 200, response.text
    done = get(activity_client, f"/learning/sessions/{sid}")["data"]
    assert done["status"] == "COMPLETED" and done["outcome"] == "PASSED" and done["next_position"] is None
    assert done["after"]["score"] is not None  # before/after for the learner
    response = activity_client.post(
        f"/api/v1/learning/sessions/{sid}/steps/1/complete", json={"completion": {}}
    )
    assert response.status_code == 409  # a finished session cannot be changed

    again = post(activity_client, "/learning/sessions", {"skill": "dsa.complexity_analysis"})["data"]
    assert again["id"] != sid and again["status"] == "ACTIVE"  # repeat after completion = a new session
    abandoned = post(activity_client, f"/learning/sessions/{again['id']}/abandon", {}, status=200)["data"]
    assert abandoned["status"] == "ABANDONED"
    with sessionmaker(bind=catalog_engine)() as session:
        actions = set(
            session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "learning_session"))
        )
    assert {
        "START_LEARNING_SESSION",
        "COMPLETE_LEARNING_STEP",
        "COMPLETE_LEARNING_SESSION",
        "ABANDON_LEARNING_SESSION",
        "SKIP_LEARNING_STEP",
    } <= actions


def test_failed_session_needs_repeat(activity_client: TestClient) -> None:
    started = post(
        activity_client, "/learning/sessions", {"skill": "dsa.complexity_analysis", "stage": "RECALL"}
    )["data"]
    assert [s["content_key"] for s in started["steps"]] == ["dsa.complexity.cards", CHECK]
    sid = started["id"]
    cards = {"completion": {"self_grades": {"0": 0, "1": 0, "2": 1, "3": 0, "4": 0}}}
    assert (
        activity_client.post(f"/api/v1/learning/sessions/{sid}/steps/1/complete", json=cards).status_code
        == 200
    )
    check = {"completion": {"answers": {"q1": [0]}}}
    result = activity_client.post(f"/api/v1/learning/sessions/{sid}/steps/2/complete", json=check).json()[
        "data"
    ]
    assert result["session"]["status"] == "COMPLETED" and result["session"]["outcome"] == "NEEDS_REPEAT"
    assert result["completion"]["passed"] is False


def test_session_from_a_plan_item_closes_it(activity_client: TestClient) -> None:
    item = get(activity_client, "/today")["data"]["plan"]["items"][0]
    started = post(
        activity_client,
        "/learning/sessions",
        {"skill": "dsa.complexity_analysis", "stage": "RECALL", "plan_item_id": item["id"]},
    )["data"]
    assert started["plan_item_id"] == item["id"]
    sid = started["id"]
    for step in started["steps"]:
        payload = (
            {"completion": {"self_grades": {str(i): 2 for i in range(5)}}}
            if step["content_type"] == "revision_card"
            else {"completion": {"answers": RIGHT, "self_grades": {"q6": 2}}}
        )
        activity_client.post(
            f"/api/v1/learning/sessions/{sid}/steps/{step['position']}/complete", json=payload
        )
    plan_item = next(
        i for i in get(activity_client, "/today")["data"]["plan"]["items"] if i["id"] == item["id"]
    )
    assert plan_item["status"] == "DONE" and plan_item["observation_type"] == "ASSESSMENT"


def test_session_needs_content(activity_client: TestClient) -> None:
    response = activity_client.post(
        "/api/v1/learning/sessions", json={"skill": "graph.mst", "stage": "TIMED"}
    )
    assert response.status_code in (201, 409)
    if response.status_code == 409:
        assert response.json()["error"]["details"]["reason"] == "NO_CONTENT"
    assert activity_client.post("/api/v1/learning/sessions", json={"skill": "ghost.x"}).status_code == 404


def test_curriculum_track_and_coverage(activity_client: TestClient) -> None:
    tracks = get(activity_client, "/learning/curriculum")["data"]
    assert [t["key"] for t in tracks][:3] == ["dsa", "python", "cs"]
    dsa = tracks[0]
    assert dsa["topics"][0]["key"] == "dsa.method"
    method = {s["key"]: s for s in dsa["topics"][0]["skills"]}
    assert method["dsa.complexity_analysis"]["coverage_state"] == "FULL"
    detail = get(activity_client, "/learning/tracks/dsa")["data"]
    assert "dsa.complexity.lesson" in [c["key"] for c in detail["content"]["dsa.method"]]
    assert activity_client.get("/api/v1/learning/tracks/nope").status_code == 404

    coverage = get(activity_client, "/learning/coverage")["data"]
    assert len(coverage["rows"]) == 133
    assert sum(coverage["summary"]["all"].values()) == 133
    row = next(r for r in coverage["rows"] if r["skill_key"] == "dsa.complexity_analysis")
    assert row["coverage_state"] == "FULL" and row["mock_coverage"] == ["DSA"]
    assert coverage["content_counts"]["lesson"] >= 2


def test_plan_shows_the_session_a_skill_mission_opens(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    """The planner is unchanged; the plan read model adds, per pending skill mission, its session."""
    from app.models import PlanItemRow, Skill

    plan = get(activity_client, "/today")["data"]["plan"]
    assert plan["learning"] == {}  # calibration plan: baseline items have their own flow
    with sessionmaker(bind=catalog_engine)() as session:
        skill_id = session.scalar(select(Skill.id).where(Skill.skill_key == "dsa.complexity_analysis"))
        row = PlanItemRow(
            plan_id=plan["id"],
            position=9,
            candidate_type="GAP",
            candidate_key="GAP:dsa.complexity_analysis",
            skill_id=skill_id,
            template_key="dsa.recall",
            stage="RECALL",
            problem_ids_json=[],
            minutes=15,
            candidate_score=50,
            reason_codes_json=[],
            explanation_json={},
            status="PENDING",
            no_evidence=False,
        )
        session.add(row)
        session.commit()
        item_id = row.id
    again = get(activity_client, "/today")["data"]["plan"]
    preview = again["learning"][str(item_id)]
    assert preview["stage"] == "RECALL" and preview["session_id"] is None
    assert [s["content_key"] for s in preview["steps"]] == ["dsa.complexity.cards", CHECK]
    assert preview["minutes"] <= 15  # fits the mission's minutes
    assert again["items"] == [
        *plan["items"],
        next(i for i in again["items"] if i["id"] == item_id),
    ]  # items untouched

    started = post(
        activity_client,
        "/learning/sessions",
        {"skill": "dsa.complexity_analysis", "stage": "RECALL", "plan_item_id": item_id},
    )["data"]
    assert (
        get(activity_client, "/today")["data"]["plan"]["learning"][str(item_id)]["session_id"]
        == started["id"]
    )


def test_mock_kits_cover_every_round_with_timed_prompts(activity_client: TestClient) -> None:
    kits = get(activity_client, "/learning/mock-kits")["data"]
    assert [k["round"] for k in kits] == [
        "DSA_1",
        "DSA_2",
        "CS_FUNDAMENTALS",
        "LLD",
        "SYSTEM_DESIGN",
        "BEHAVIORAL",
        "PROJECT_DEEP_DIVE",
    ]  # the existing loop; the final simulation is the full mock
    dsa = kits[0]
    assert dsa["round_type"] == "DSA" and dsa["minutes"] == 45 and dsa["components"] == ["dsa", "coding"]
    keys = [i["key"] for i in dsa["items"]]
    assert "dsa.complexity.compare" in keys or "dsa.complexity.exercise" in keys
    assert all(i["time_limit_seconds"] or i["type"] == "timed_problem" for k in kits for i in k["items"])
    assert len({i["skills"][0] for i in dsa["items"]}) == len(dsa["items"])  # one prompt per skill
    assert len(dsa["focus_skills"]) == 3


def test_skill_focus_names_one_observation_kind_even_when_the_template_allows_several(
    activity_client: TestClient,
) -> None:
    focus = get(activity_client, "/skills/dsa.complexity_analysis")["data"]["focus"]
    assert focus is not None and focus["observation_kind"] in ("STUDY_SESSION", "RECALL_QUIZ", "ATTEMPT")
    assert "[" not in focus["observation_kind"]
