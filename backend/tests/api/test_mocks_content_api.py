"""Slice 10 end to end: mocks -> L7 evidence, mock-weakness pressure, MOCKW revision items, G6/G9; content."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog
from tests.api.test_activity_api import get, post

pytestmark = pytest.mark.db


def sd_mock(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "source": "PEER",
        "occurred_at": "2026-10-03T10:00:00Z",
        "rounds": [
            {
                "round_type": "SYSTEM_DESIGN",
                "duration_minutes": 45,
                "round_score": 58,
                "skills": [
                    {"skill": "sd.capacity_estimation", "outcome_points": 40, "is_weakness": True},
                    {"skill": "sd.caching", "outcome_points": 55, "is_weakness": True},
                    {"skill": "sd.api_design", "outcome_points": 80},
                ],
            }
        ],
    }
    body.update(overrides)
    return body


def patch(client: TestClient, path: str, body: dict[str, Any], status: int = 200) -> dict[str, Any]:
    response = client.patch(f"/api/v1{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


def test_mock_round_feeds_every_engine(activity_client: TestClient) -> None:
    body = post(activity_client, "/mocks", sd_mock())
    mock = body["data"]
    assert (mock["occurred_on"], mock["source"], len(mock["rounds"])) == ("2026-10-03", "PEER", 1)
    round_id = mock["rounds"][0]["id"]
    deltas = {d["skill_key"]: d for d in body["effects"]["skill_deltas"]}
    assert deltas["sd.capacity_estimation"]["after"]["score"] is not None  # L7 evidence row exists
    changes = {c["item_key"]: c for c in body["effects"]["revision_changes"]}
    assert changes[f"MOCKW:{round_id}:sd.capacity_estimation"]["due_date"] == "2026-10-05"  # MOCKW ladder +2
    assert f"MOCKW:{round_id}:sd.caching" in changes and f"MOCKW:{round_id}:sd.api_design" not in changes
    evidence = get(activity_client, "/skills/sd.capacity_estimation")["data"]["evidence"]
    assert evidence[0]["source_type"] == "MOCK_ROUND" and evidence[0]["level"] == 7
    assert evidence[0]["source_key"] == f"mock_round:{round_id}" and evidence[0]["is_weakness"] is True
    gap = get(activity_client, "/gaps/sd.capacity_estimation")["data"]
    assert "MOCK_WEAKNESS" in gap["reason_codes"]
    readiness = get(activity_client, "/readiness")["data"]
    g6 = [c["message"] for c in readiness["all_failing"] if c["gate"] == "G6"]
    assert "SYSTEM_DESIGN latest round 58 < 65" in g6
    summary = get(activity_client, "/mocks/summary")["data"]
    sd = next(t for t in summary["by_type"] if t["round_type"] == "SYSTEM_DESIGN")
    assert (sd["rounds_60d"], sd["latest"]["score"], sd["required_60d"]) == (1, 58, 2)
    assert "SYSTEM_DESIGN latest round 58 < 65" in sd["g6_failing"] and summary["g6_passed"] is False


def test_self_mock_outcome_is_capped_at_80(activity_client: TestClient) -> None:
    body = sd_mock(source="SELF")
    body["rounds"][0]["skills"] = [{"skill": "sd.caching", "outcome_points": 95}]
    body["rounds"][0]["round_score"] = 95
    post(activity_client, "/mocks", body)
    row = get(activity_client, "/skills/sd.caching")["data"]["evidence"][0]
    assert (row["level"], row["outcome_points"]) == (7, 80)
    sd = next(
        t
        for t in get(activity_client, "/mocks/summary")["data"]["by_type"]
        if t["round_type"] == "SYSTEM_DESIGN"
    )
    assert sd["latest"]["score"] == 80 and sd["non_self_60d"] == 0


@pytest.mark.parametrize(
    ("skills", "message"),
    [
        ([{"skill": "db.indexing", "outcome_points": 50}], "cannot score cs skill"),
        ([{"skill": "no.such", "outcome_points": 50}], "unknown or inactive skill"),
        (
            [{"skill": "sd.caching", "outcome_points": 50}, {"skill": "sd.caching", "outcome_points": 60}],
            "listed twice",
        ),
    ],
)
def test_mock_validation(activity_client: TestClient, skills: list[dict[str, Any]], message: str) -> None:
    body = sd_mock()
    body["rounds"][0]["skills"] = skills
    error = post(activity_client, "/mocks", body, status=422)["error"]
    assert any(message in e["msg"] for e in error["details"]["errors"]), error


def test_final_simulation_validity_and_g9_progress(activity_client: TestClient) -> None:
    rounds = [
        {"round_type": rt, "duration_minutes": 30, "round_score": 80, "skills": []}
        for rt in ("DSA", "CS", "BEHAVIORAL", "PROJECT_DEEP_DIVE", "SYSTEM_DESIGN")
    ]
    post(
        activity_client,
        "/mocks",
        {
            "source": "PEER",
            "is_final_simulation": True,
            "rounds": rounds,
            "occurred_at": "2026-10-02T08:00:00Z",
        },
    )
    post(
        activity_client,
        "/mocks",
        {
            "source": "PEER",
            "is_final_simulation": True,
            "rounds": rounds[:2],
            "occurred_at": "2026-10-03T08:00:00Z",
        },
    )
    summary = get(activity_client, "/mocks/summary")["data"]
    finals = summary["final_simulations"]
    assert [(f["date"], f["valid"], f["passed"]) for f in finals] == [
        ("2026-10-03", False, False),
        ("2026-10-02", True, True),
    ]
    assert summary["g9_failing"] == ["1 of 3 final simulations"]


def test_mock_correction_supersedes(activity_client: TestClient) -> None:
    first = post(activity_client, "/mocks", sd_mock())["data"]
    corrected = post(activity_client, f"/mocks/{first['id']}/corrections", sd_mock(source="PLATFORM"))["data"]
    assert corrected["supersedes_id"] == first["id"]
    assert [m["id"] for m in get(activity_client, "/mocks")["data"]] == [corrected["id"]]
    again = post(activity_client, f"/mocks/{first['id']}/corrections", sd_mock(), status=409)
    assert again["error"]["details"]["latest_mock_id"] == corrected["id"]


def test_story_creates_revision_item_and_edits_are_audited(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    story = {
        "title": "Owned the outage fix",
        "situation": "s",
        "task": "t",
        "action": "a",
        "result": "r",
        "metric": "p95 2 s -> 300 ms",
        "tradeoffs": "Shipped a cache before the query rewrite.",
        "learning": "Alert on symptoms first.",
        "competencies": ["behavioral.ownership", "communication.structured_answers"],
    }
    body = post(activity_client, "/stories", story)
    sid = body["data"]["id"]
    # the seven parts of an evidence-based story (MASTER_SPEC_V3 §19)
    assert (body["data"]["metric"], body["data"]["tradeoffs"], body["data"]["learning"]) == (
        "p95 2 s -> 300 ms",
        "Shipped a cache before the query rewrite.",
        "Alert on symptoms first.",
    )
    assert body["data"]["competencies"] == ["behavioral.ownership", "communication.structured_answers"]
    change = {c["item_key"]: c for c in body["effects"]["revision_changes"]}[f"STORY:{sid}"]
    assert change["due_date"] == "2026-10-05"
    items = activity_client.get("/api/v1/revisions").json()["data"]["items"]
    story_item = next(i for i in items if i["item_key"] == f"STORY:{sid}")
    assert (story_item["skill"], story_item["minutes"], story_item["review_kind"]) == (
        "behavioral.ownership",
        10,
        "STORY_REHEARSAL",
    )
    bad = post(activity_client, "/stories", {**story, "competencies": ["db.indexing"]}, status=422)
    assert "not a behavioral/communication skill" in str(bad)
    patched = patch(activity_client, f"/stories/{sid}", {"title": "Owned the fix", "archived": True})["data"]
    assert (patched["title"], patched["archived"]) == ("Owned the fix", True)
    assert get(activity_client, "/stories")["meta"]["count"] == 1
    with sessionmaker(bind=catalog_engine)() as session:
        actions = sorted(session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "story")))
    assert actions == ["CREATE_STORY", "UPDATE_STORY"]


def test_projects_and_prompts(activity_client: TestClient) -> None:
    project = post(
        activity_client, "/projects", {"project_key": "payments-api", "name": "Payments API", "summary": "x"}
    )["data"]
    assert project["project_key"] == "payments-api"
    post(
        activity_client,
        "/projects",
        {"project_key": "payments-api", "name": "Dup", "summary": "x"},
        status=409,
    )
    assert patch(activity_client, "/projects/payments-api", {"summary": "new"})["data"]["summary"] == "new"
    prompt = post(
        activity_client,
        "/prompts",
        {
            "prompt_key": "db-mvcc-1",
            "skill": "db.isolation_mvcc",
            "kind": "CONCEPT_EXPLAIN",
            "prompt_text": "Explain MVCC",
        },
    )["data"]
    assert prompt["source_key"] == "prompt:db-mvcc-1"
    post(
        activity_client,
        "/prompts",
        {"prompt_key": "bad", "skill": "db.indexing", "kind": "STORY_REHEARSAL", "prompt_text": "x"},
        status=422,
    )
    assert get(activity_client, "/prompts", skill="db.isolation_mvcc")["meta"]["count"] == 1
