"""Slice 6 behavior through the API: item creation, linked reviews, buckets, manual actions, replay."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog
from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db


def items(client: TestClient, **params: Any) -> dict[str, dict[str, Any]]:
    data = client.get("/api/v1/revisions", params=params).json()["data"]
    return {i["item_key"]: i for i in data["items"]}


def test_canonical_solve_creates_problem_item_and_linked_review_moves_it(activity_client: TestClient) -> None:
    body = post(activity_client, "/problem-attempts", SOLVED)  # Two Sum: canonical, EASY, clean 18/15 min
    changes = {c["item_key"]: c for c in body["effects"]["revision_changes"]}
    assert changes["PROBLEM:1"] == {"item_key": "PROBLEM:1", "change": "CREATED", "due_date": "2026-10-11"}
    listing = activity_client.get("/api/v1/revisions").json()
    data = listing["data"]
    assert (data["backlog_minutes"], data["cap_minutes"], data["triage_threshold_minutes"]) == (0, 36, 504)
    problem = {i["item_key"]: i for i in data["items"]}["PROBLEM:1"]
    assert (problem["bucket"], problem["interval_index"], problem["minutes"], problem["review_kind"]) == (
        "upcoming",
        2,
        15,
        "ATTEMPT",
    )
    assert listing["meta"]["run_id"] >= 1

    review = post(
        activity_client,
        "/problem-attempts",
        {**SOLVED, "time_seconds": 600, "mode": "REVISION", "revision_item_key": "PROBLEM:1"},
    )
    moved = {c["item_key"]: c for c in review["effects"]["revision_changes"]}["PROBLEM:1"]
    assert moved == {
        "item_key": "PROBLEM:1",
        "change": "UPDATED",
        "state": "ACTIVE",
        "due_date": "2026-10-18",
    }
    assert items(activity_client)["PROBLEM:1"]["interval_index"] == 3


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"revision_item_key": "PROBLEM:999"}, "unknown revision item"),
        ({"battery_item_key": "M0-B99"}, "unknown baseline battery item"),
    ],
)
def test_link_keys_are_validated(activity_client: TestClient, body: dict[str, Any], message: str) -> None:
    error = post(activity_client, "/problem-attempts", {**SOLVED, **body}, status=422)["error"]
    assert any(message in e["msg"] for e in error["details"]["errors"])


def test_problem_item_is_reviewed_only_by_its_problem(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    error = post(
        activity_client,
        "/problem-attempts",
        {**SOLVED, "problem_id": 2, "revision_item_key": "PROBLEM:1"},
        status=422,
    )
    assert "reviewed by an attempt on that problem" in str(error)


def test_manual_suspend_and_resume_are_audited_and_replayed(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    suspended = post(activity_client, "/revisions/PROBLEM:1/suspend", {}, status=200)
    assert (suspended["data"]["state"], suspended["data"]["suspend_reason"], suspended["data"]["bucket"]) == (
        "SUSPENDED",
        "MANUAL",
        "suspended",
    )
    again = post(activity_client, "/revisions/PROBLEM:1/suspend", {}, status=409)
    assert again["error"]["code"] == "INVALID_STATE"
    resumed = post(activity_client, "/revisions/PROBLEM:1/resume", {}, status=200)["data"]
    assert (resumed["state"], resumed["due_date"], resumed["bucket"]) == ("ACTIVE", "2026-10-04", "due")
    before = items(activity_client)
    post(activity_client, "/admin/rebuild", {}, status=200)
    assert items(activity_client) == before  # actions are raw rows; the projection replays them
    with sessionmaker(bind=catalog_engine)() as session:
        actions = session.scalars(
            select(AuditLog.action).where(AuditLog.entity_type == "revision_item")
        ).all()
        assert sorted(actions) == ["RESUME_REVISION_ITEM", "SUSPEND_REVISION_ITEM"]
    with catalog_engine.connect() as connection:
        rows = connection.execute(text("SELECT action, reason FROM revision_item_actions ORDER BY id")).all()
    assert [tuple(r) for r in rows] == [("SUSPEND", "MANUAL"), ("RESUME", "MANUAL")]
    post(activity_client, "/revisions/NOPE:1/resume", {}, status=404)


def test_bucket_filter_and_unknown_bucket(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    assert set(items(activity_client, bucket="upcoming")) >= {"PROBLEM:1"}
    assert items(activity_client, bucket="overdue") == {}
    assert activity_client.get("/api/v1/revisions", params={"bucket": "later"}).status_code == 422


def test_assessment_review_of_a_concept_item(activity_client: TestClient) -> None:
    concept = {
        "kind": "CONCEPT_EXPLAIN",
        "source_key": "prompt:db-indexing",
        "skills": [{"skill": "db.indexing", "outcome_points": 95}],
        "observed_at": "2026-10-01T06:00:00Z",
    }
    created = post(activity_client, "/assessments", concept)["effects"]["revision_changes"]
    assert {"item_key": "CS:db.indexing", "change": "CREATED", "due_date": "2026-10-08"} in created
    fail = post(
        activity_client,
        "/assessments",
        {
            **concept,
            "observed_at": "2026-10-04T06:00:00Z",
            "revision_item_key": "CS:db.indexing",
            "skills": [{"skill": "db.indexing", "outcome_points": 30}],
        },
    )
    item = items(activity_client)["CS:db.indexing"]
    assert (item["interval_index"], item["lapses"], item["needs_reinforcement"], item["minutes"]) == (
        0,
        1,
        True,
        20,
    )
    assert get(activity_client, "/gaps/db.indexing")["data"]["skill_key"] == "db.indexing"
    assert fail["effects"]["revision_changes"]
