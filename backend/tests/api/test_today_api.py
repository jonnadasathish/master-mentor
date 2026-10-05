"""Slice 7 behavior through the API: frozen daily plan, item actions, regenerate, carry-over, determinism."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_clock
from app.infrastructure.db import get_session
from app.main import create_app
from app.models import AuditLog
from app.services.seed_service import SeedLoader
from tests.api.test_activity_api import SOLVED
from tests.catalog_helpers import SEED_DIR

pytestmark = pytest.mark.db
API = "/api/v1"


@dataclass
class MovableClock:
    instant: datetime

    def now_utc(self) -> datetime:
        return self.instant


@pytest.fixture
def plan_env(catalog_engine: Engine) -> Iterator[tuple[TestClient, MovableClock]]:
    clock = MovableClock(datetime(2026, 10, 4, 6, 0, tzinfo=UTC))  # Sunday in Asia/Kolkata
    factory = sessionmaker(bind=catalog_engine)
    with factory() as session:
        SeedLoader(session, clock).load(SEED_DIR)

    def _session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, clock


def call(
    client: TestClient, method: str, path: str, body: dict[str, Any] | None = None, status: int = 200
) -> Any:
    response = client.request(method, f"{API}{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


def today(client: TestClient) -> dict[str, Any]:
    return call(client, "GET", "/today")["data"]


def test_cold_start_plan_is_the_battery_and_is_frozen(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, _ = plan_env
    call(client, "POST", "/goals", {"target_date": "2027-06-28"}, status=201)
    first = today(client)
    plan = first["plan"]
    assert [(i["candidate_key"], i["minutes"]) for i in plan["items"]] == [
        ("BASE:M0-B01", 15),
        ("BASE:M0-B02", 60),
    ]
    # Sunday budget 75 => B01 + B02 = 75, nothing else fits
    assert (plan["budget_minutes"], plan["allocated_minutes"], plan["unallocated_minutes"]) == (75, 75, 0)
    assert plan["message"]["rule"] == "CALIBRATION" and first["calibration"]["active"] is True
    assert [p["key"] for p in plan["items"][1]["problems"]] == ["LEETCODE:3sum", "LEETCODE:group-anagrams"]
    call(client, "POST", "/problem-attempts", SOLVED, status=201)  # mid-day observation
    again = today(client)
    assert again["plan"]["id"] == plan["id"] and again["plan"]["items"] == plan["items"]  # plan never changes


def test_complete_with_observation_and_no_evidence(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, _ = plan_env
    items = today(client)["plan"]["items"]
    b01, b02 = items[0]["id"], items[1]["id"]
    done = call(client, "POST", f"/plan/items/{b01}/complete", {"no_evidence": True})
    assert done["data"]["item"]["status"] == "DONE" and done["data"]["item"]["no_evidence"] is True
    body = {"outcome": "PASS", "time_seconds": 1500, "timed": True, "time_limit_seconds": 1800}
    completed = call(
        client, "POST", f"/plan/items/{b02}/complete", {"observation": {"type": "ATTEMPT", "body": body}}
    )
    item, observation = completed["data"]["item"], completed["data"]["observation"]
    assert (item["status"], item["observation_type"]) == ("DONE", "ATTEMPT")
    assert observation["battery_item_key"] == "M0-B02" and observation["problem"]["key"] == "LEETCODE:3sum"
    assert completed["effects"]["skill_deltas"], "the linked observation feeds the engines"
    baseline = call(client, "GET", "/baseline")["data"]
    assert [i["complete"] for i in baseline["items"][:2]] == [True, True]
    call(client, "POST", f"/plan/items/{b02}/complete", {"no_evidence": True}, status=409)
    bad = call(client, "POST", f"/plan/items/{b01}/skip", {"skip_reason": "LAZY"}, status=422)
    assert bad["error"]["code"] == "VALIDATION_ERROR"
    with sessionmaker(bind=catalog_engine)() as session:
        actions = sorted(session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "plan_item")))
        assert actions == ["COMPLETE_PLAN_ITEM", "COMPLETE_PLAN_ITEM"]
        linked = session.execute(text("SELECT plan_item_id FROM problem_attempts")).scalar_one()
        assert linked == b02


def test_complete_requires_exactly_one_of_observation_or_no_evidence(
    plan_env: tuple[TestClient, MovableClock],
) -> None:
    client, _ = plan_env
    item = today(client)["plan"]["items"][0]["id"]
    call(client, "POST", f"/plan/items/{item}/complete", {}, status=422)
    error = call(
        client,
        "POST",
        f"/plan/items/{item}/complete",
        {"observation": {"type": "ATTEMPT", "body": {"outcome": "WIN"}}},
        status=422,
    )
    assert error["error"]["details"]["errors"][0]["loc"][:2] == ["body", "observation"]


def test_skip_defer_and_carry_over_next_day(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, clock = plan_env
    items = today(client)["plan"]["items"]
    skipped = call(client, "POST", f"/plan/items/{items[0]['id']}/skip", {"skip_reason": "NO_TIME"})["data"]
    assert (skipped["status"], skipped["skip_reason"]) == ("SKIPPED", "NO_TIME")
    deferred = call(client, "POST", f"/plan/items/{items[1]['id']}/defer")["data"]
    assert deferred["status"] == "DEFERRED"
    call(client, "POST", f"/plan/items/{items[1]['id']}/defer", status=409)
    clock.instant += timedelta(days=1)  # Monday
    tomorrow = today(client)["plan"]
    keys = [i["candidate_key"] for i in tomorrow["items"]]
    assert "BASE:M0-B01" in keys and "BASE:M0-B02" in keys  # battery items are re-offered
    carried = next(i for i in tomorrow["items"] if i["candidate_key"] == "BASE:M0-B02")
    assert carried["carried_over_from_id"] == items[1]["id"]
    history = call(client, "GET", "/plan/2026-10-04")["data"]
    assert [i["status"] for i in history["items"]] == ["SKIPPED", "DEFERRED"]
    call(client, "GET", "/plan/2026-01-01", status=404)


def test_regenerate_keeps_done_items_and_discards_pending(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, _ = plan_env
    plan = today(client)["plan"]
    first = plan["items"][0]["id"]
    call(client, "POST", f"/plan/items/{first}/complete", {"no_evidence": True})
    regenerated = call(client, "POST", "/plan/today/regenerate")["data"]["plan"]
    assert regenerated["regenerated_count"] == 1
    statuses = {i["candidate_key"]: i["status"] for i in regenerated["items"]}
    assert statuses["BASE:M0-B01"] == "DONE"
    assert [i["candidate_key"] for i in regenerated["items"]].count(
        "BASE:M0-B01"
    ) == 1  # kept work is not re-planned
    assert regenerated["items"][0]["id"] == first
    positions = [i["position"] for i in regenerated["items"]]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(AuditLog.action).where(AuditLog.action == "REGENERATE_PLAN"))
        discarded = session.execute(
            text("SELECT COUNT(*) FROM plan_items WHERE status = 'DISCARDED'")
        ).scalar_one()
        assert discarded == 1  # the old pending B02 is kept for history


def test_same_inputs_generate_the_same_plan(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, _ = plan_env
    call(client, "POST", "/problem-attempts", {**SOLVED, "attempted_at": "2026-10-03T06:00:00Z"}, status=201)
    first = today(client)["plan"]
    with catalog_engine.begin() as connection:
        before = connection.execute(text("SELECT input_hash FROM daily_plans")).scalar_one()
        connection.execute(text("DELETE FROM plan_items"))
        connection.execute(text("DELETE FROM daily_plans"))
    second = today(client)["plan"]
    strip = lambda items: [{k: v for k, v in i.items() if k != "id"} for i in items]  # noqa: E731
    assert strip(second["items"]) == strip(first["items"]) and second["message"] == first["message"]
    with catalog_engine.connect() as connection:
        assert connection.execute(text("SELECT input_hash FROM daily_plans")).scalar_one() == before


def test_complete_with_mock_observation(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, _ = plan_env
    item = today(client)["plan"]["items"][0]["id"]
    body = {
        "source": "PEER",
        "rounds": [
            {
                "round_type": "CS",
                "duration_minutes": 30,
                "round_score": 72,
                "skills": [{"skill": "db.indexing", "outcome_points": 70}],
            }
        ],
    }
    done = call(
        client, "POST", f"/plan/items/{item}/complete", {"observation": {"type": "MOCK", "body": body}}
    )
    assert (done["data"]["item"]["status"], done["data"]["item"]["observation_type"]) == ("DONE", "MOCK")
    assert done["data"]["observation"]["rounds"][0]["round_type"] == "CS"
    mocks = call(client, "GET", "/mocks")["data"]
    assert len(mocks) == 1
