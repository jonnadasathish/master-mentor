"""Cross-track communication (D-087): an optional "explain it aloud" step after technical practice.

It is a normal content step on the existing learning session. It must never block the technical task, never
supply the observation that closes the plan item, and never touch technical evidence."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Assessment, AssessmentSkill, Skill, SpeakingPractice
from tests.api.test_activity_api import get, post

pytestmark = pytest.mark.db
TECH = "dsa.complexity_analysis"
EXERCISE = "dsa.complexity.exercise"
EXPLAIN = "comm.explain_code.explain_complexity"
COMM_SKILL = "comm.explain_code"
SAID = (
    "First, the function loops over the list once, so the time is order n. Because it stores each value in a "
    "set, the space is also order n. For example, a list of one thousand numbers needs one thousand set "
    "entries. Finally, the nested version would be order n squared, so I chose the single pass."
)


def start(
    client: TestClient, skill: str = TECH, stage: str = "INDEPENDENT", budget: int = 60, **extra: Any
) -> dict[str, Any]:
    return post(
        client, "/learning/sessions", {"skill": skill, "stage": stage, "budget_minutes": budget, **extra}
    )["data"]


def complete(client: TestClient, sid: int, position: int, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/api/v1/learning/sessions/{sid}/steps/{position}/complete", json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"]["session"]


def exercise_body(client: TestClient) -> dict[str, Any]:
    rubric = get(client, f"/learning/content/{EXERCISE}")["data"]["rubric"]
    return {"completion": {"ratings": {r["key"]: 2 for r in rubric}}}


def explain_body(client: TestClient) -> dict[str, Any]:
    rubric = get(client, f"/learning/content/{EXPLAIN}")["data"]["rubric"]
    return {
        "completion": {
            "ratings": {r["key"]: 2 for r in rubric},
            "speech": {"source": "BROWSER", "transcript": SAID, "duration_seconds": 50},
        }
    }


def assessment_count(engine: Engine) -> int:
    with sessionmaker(bind=engine)() as session:
        return int(session.scalar(select(func.count()).select_from(Assessment)) or 0)


def plan_item(client: TestClient, item_id: int) -> dict[str, Any]:
    return next(i for i in get(client, "/today")["data"]["plan"]["items"] if i["id"] == item_id)


def skills_of(engine: Engine, assessment_id: int) -> set[str]:
    with sessionmaker(bind=engine)() as session:
        rows = session.scalars(
            select(Skill.skill_key)
            .join(AssessmentSkill, AssessmentSkill.skill_id == Skill.id)
            .where(AssessmentSkill.assessment_id == assessment_id)
        )
        return set(rows)


def evidence_count(client: TestClient, key: str) -> int:
    return len(get(client, f"/skills/{key}")["data"]["evidence"])


# --------------------------------------------------------------------------------------------- shape


def test_a_technical_session_ends_with_one_optional_explain_step_before_the_reflection(
    activity_client: TestClient,
) -> None:
    steps = start(activity_client)["steps"]
    assert [(s["kind"], s["content_key"], s["optional"]) for s in steps] == [
        ("CONTENT", EXERCISE, False),
        ("CONTENT", EXPLAIN, True),
        ("REFLECTION", None, False),
    ]


def test_the_step_appears_only_where_it_makes_sense(activity_client: TestClient) -> None:
    learn = start(activity_client, stage="LEARN")
    assert not any(s["optional"] for s in learn["steps"])  # nothing to explain yet
    post(activity_client, f"/learning/sessions/{learn['id']}/abandon", {}, status=200)
    own = start(activity_client, skill=COMM_SKILL, stage="INDEPENDENT")["steps"]
    assert not any(s["optional"] for s in own)  # a communication session has its own required practice


@pytest.mark.parametrize("budget", [15, 17, 18, 20, 30, 60])
def test_the_explain_step_never_exceeds_the_time_budget(activity_client: TestClient, budget: int) -> None:
    session = start(activity_client, budget=budget)
    steps = session["steps"]
    required = sum(s["minutes"] for s in steps if not s["optional"] and s["kind"] != "REFLECTION")
    total = sum(s["minutes"] for s in steps if s["kind"] != "REFLECTION")
    assert total <= max(budget, required)  # the optional step only ever fits inside the budget
    if budget < required + 3:
        assert not any(s["optional"] for s in steps)


def test_the_today_preview_marks_the_optional_step(activity_client: TestClient) -> None:
    plan = get(activity_client, "/today")["data"]["plan"]
    for preview in plan.get("learning", {}).values():
        assert all(isinstance(s["optional"], bool) for s in preview["steps"])


# ---------------------------------------------------------------------------------- completion / skip


def test_technical_work_closes_the_plan_item_without_the_explain_step(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    item = get(activity_client, "/today")["data"]["plan"]["items"][0]
    session = start(activity_client, plan_item_id=item["id"])
    sid = session["id"]
    technical = complete(activity_client, sid, 1, exercise_body(activity_client))
    technical_assessment = technical["steps"][0]["observation_id"]
    done = complete(activity_client, sid, 3, {"reflection": "Count operations, not loops."})
    assert done["status"] == "ACTIVE" and done["next_position"] == 2  # the optional step is still available
    closed = plan_item(activity_client, item["id"])
    assert closed["status"] == "DONE" and closed["observation_id"] == technical_assessment
    assert closed["observation_type"] == "ASSESSMENT"


def test_skipping_the_explain_step_completes_the_session_and_records_nothing(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    item = get(activity_client, "/today")["data"]["plan"]["items"][0]
    sid = start(activity_client, plan_item_id=item["id"])["id"]
    complete(activity_client, sid, 1, exercise_body(activity_client))
    complete(activity_client, sid, 3, {"reflection": "ok"})
    before = assessment_count(catalog_engine)
    skipped = post(activity_client, f"/learning/sessions/{sid}/steps/2/skip", {}, status=200)["data"]
    assert skipped["status"] == "COMPLETED" and skipped["outcome"] == "PASSED"
    assert skipped["steps"][1]["status"] == "SKIPPED" and skipped["steps"][1]["observation_id"] is None
    assert assessment_count(catalog_engine) == before  # no fake or duplicate evidence
    assert plan_item(activity_client, item["id"])["status"] == "DONE"
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(func.count()).select_from(SpeakingPractice)) == 0


def test_completing_the_explain_step_adds_communication_evidence_and_leaves_technical_evidence_alone(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    item = get(activity_client, "/today")["data"]["plan"]["items"][0]
    sid = start(activity_client, plan_item_id=item["id"])["id"]
    technical = complete(activity_client, sid, 1, exercise_body(activity_client))
    technical_id = technical["steps"][0]["observation_id"]
    technical_state = get(activity_client, f"/skills/{TECH}")["data"]["state"]
    tech_rows = evidence_count(activity_client, TECH)
    complete(activity_client, sid, 3, {"reflection": "ok"})
    after_reflection = plan_item(activity_client, item["id"])

    done = complete(activity_client, sid, 2, explain_body(activity_client))
    spoken_id = done["steps"][1]["observation_id"]
    assert done["status"] == "COMPLETED" and spoken_id != technical_id
    assert skills_of(catalog_engine, spoken_id) == {COMM_SKILL}  # never a technical assessment
    assert TECH not in skills_of(catalog_engine, spoken_id) and COMM_SKILL not in skills_of(
        catalog_engine, technical_id
    )
    assert evidence_count(activity_client, TECH) == tech_rows  # technical evidence untouched
    assert get(activity_client, f"/skills/{TECH}")["data"]["state"] == technical_state
    assert ("CONCEPT_EXPLAIN", 3) in {
        (e["kind"], e["level"]) for e in get(activity_client, f"/skills/{COMM_SKILL}")["data"]["evidence"]
    }
    again = plan_item(activity_client, item["id"])
    assert again == after_reflection and again["observation_id"] == technical_id  # closure never moved
    with sessionmaker(bind=catalog_engine)() as session:
        (row,) = session.scalars(select(SpeakingPractice)).all()
        assert row.assessment_id == spoken_id and row.source == "BROWSER"


def test_the_same_event_cannot_record_the_explain_step_twice(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    sid = start(activity_client)["id"]
    complete(activity_client, sid, 2, explain_body(activity_client))
    count = assessment_count(catalog_engine)
    again = activity_client.post(
        f"/api/v1/learning/sessions/{sid}/steps/2/complete", json=explain_body(activity_client)
    )
    assert again.status_code == 409  # the step is already DONE
    assert assessment_count(catalog_engine) == count


def test_a_finished_technical_session_does_not_offer_the_same_communication_skill_again(
    activity_client: TestClient,
) -> None:
    sid = start(activity_client)["id"]
    complete(activity_client, sid, 2, explain_body(activity_client))
    post(activity_client, f"/learning/sessions/{sid}/abandon", {}, status=200)
    next_steps = start(activity_client)["steps"]
    assert not any(
        s["optional"] for s in next_steps
    )  # the communication skill was practised in the last 3 days


def test_an_old_session_with_only_the_optional_step_left_is_settled_when_new_work_starts(
    activity_client: TestClient,
) -> None:
    items = get(activity_client, "/today")["data"]["plan"]["items"]
    assert len(items) >= 2
    first = start(activity_client, plan_item_id=items[0]["id"])
    complete(activity_client, first["id"], 1, exercise_body(activity_client))
    complete(activity_client, first["id"], 3, {"reflection": "ok"})
    assert get(activity_client, f"/learning/sessions/{first['id']}")["data"]["status"] == "ACTIVE"
    second = start(activity_client, plan_item_id=items[1]["id"])
    assert second["id"] != first["id"]
    settled = get(activity_client, f"/learning/sessions/{first['id']}")["data"]
    assert settled["status"] == "COMPLETED" and settled["steps"][1]["status"] == "SKIPPED"
    assert plan_item(activity_client, items[0]["id"])["status"] == "DONE"
