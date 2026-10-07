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
    # greedy cover over the seed-v2 bank (the golden scenarios stay pinned to the original problems, D-084)
    assert [p["key"] for p in plan["items"][1]["problems"]] == [
        "LEETCODE:3sum",
        "LEETCODE:continuous-subarray-sum",
    ]
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


def test_week_context_is_read_only_and_counts_recorded_practice(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, clock = plan_env  # Sunday 2026-10-04 (Asia/Kolkata)
    empty = call(client, "GET", "/today/week")["data"]
    assert (empty["week_start"], empty["week_end"], empty["plan_date"]) == (
        "2026-09-28",
        "2026-10-04",
        "2026-10-04",
    )
    assert (empty["preparation_day"], empty["target_minutes"], empty["practice_minutes"]) == (None, None, 0)
    assert empty["revision"] == {"planned": 0, "done": 0, "completion_pct": None}
    with sessionmaker(bind=catalog_engine)() as session:
        plans = session.execute(text("SELECT COUNT(*) FROM daily_plans")).scalar_one()
        assert plans == 0  # reading the week creates no plan
        assert session.execute(text("SELECT COUNT(*) FROM mentor_runs")).scalar_one() == 0

    call(client, "POST", "/goals", {"target_date": "2027-06-28"}, status=201)
    call(client, "POST", "/problem-attempts", SOLVED, status=201)  # 18 min on a DSA skill, today
    week = call(client, "GET", "/today/week")["data"]
    assert (week["preparation_day"], week["practice_minutes"], week["active_days"]) == (1, 18, 1)
    assert week["target_minutes"] == 600
    tracks = {t["track"]: t for t in week["minutes_by_track"]}
    assert tracks["dsa_coding"]["minutes"] == 18 and tracks["dsa_coding"]["weekly_target"] > 0
    assert sum(t["minutes"] for t in tracks.values()) == 18

    clock.instant += timedelta(days=1)  # Monday: a new week starts empty; the preparation day advances
    monday = call(client, "GET", "/today/week")["data"]
    assert (monday["week_start"], monday["practice_minutes"], monday["active_days"]) == ("2026-10-05", 0, 0)
    assert monday["preparation_day"] == 2


# ---------------------------------------------------- battery work recorded outside the plan (D-082)


def _sweep(client: TestClient, request_id: str) -> dict[str, Any]:
    required = call(client, "GET", "/catalog/role-profile/targets?required=true")["data"]
    entries = [{"skill": t["skill"], "familiarity": "SOME"} for t in required]
    return call(
        client,
        "POST",
        "/assessments/self-assessment-sweep",
        {"entries": entries, "client_request_id": request_id},
        status=201,
    )


def _item(client: TestClient, candidate_key: str) -> dict[str, Any]:
    return next(i for i in today(client)["plan"]["items"] if i["candidate_key"] == candidate_key)


def _plan_item_audits(catalog_engine: Engine) -> list[tuple[str, str]]:
    with sessionmaker(bind=catalog_engine)() as session:
        rows = session.execute(
            select(AuditLog.entity_id, AuditLog.action).where(AuditLog.entity_type == "plan_item")
        ).all()
        return [(str(r[0]), str(r[1])) for r in rows]


def test_the_sweep_completes_its_plan_item(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, _ = plan_env
    b01 = _item(client, "BASE:M0-B01")
    assert b01["status"] == "PENDING"
    call(client, "POST", f"/plan/items/{b01['id']}/start")
    created = _sweep(client, "sweep-first")["data"]

    item = _item(client, "BASE:M0-B01")
    assert (item["status"], item["observation_type"], item["observation_id"]) == (
        "DONE",
        "ASSESSMENT",
        created[0]["id"],
    )
    assert item["no_evidence"] is False and item["completed_at"] is not None
    assert today(client)["plan"]["done_minutes"] == 15
    assert _item(client, "BASE:M0-B02")["status"] == "PENDING"  # only the matching battery item
    assert _plan_item_audits(catalog_engine) == [(str(b01["id"]), "COMPLETE_PLAN_ITEM")]
    with sessionmaker(bind=catalog_engine)() as session:
        linked = set(session.scalars(text("SELECT DISTINCT plan_item_id FROM assessments")))
        assert linked == {b01["id"]}

    # a later sweep is recorded normally and never completes (or audits) the item twice
    _sweep(client, "sweep-second")
    assert _item(client, "BASE:M0-B01")["observation_id"] == created[0]["id"]
    assert _plan_item_audits(catalog_engine) == [(str(b01["id"]), "COMPLETE_PLAN_ITEM")]


def test_the_sweep_counts_in_the_weekly_plan_completion(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, clock = plan_env
    today(client)  # Sunday 2026-10-04: B01 (15) + B02 (60)
    _sweep(client, "sweep-week")
    clock.instant += timedelta(days=1)  # Monday: the week 2026-09-28..10-04 is complete
    metrics = call(client, "GET", "/weekly-reviews/latest")["data"]["metrics"]
    assert (metrics["week_start"], metrics["planned_minutes"], metrics["completed_minutes"]) == (
        "2026-09-28",
        75,
        15,
    )
    assert metrics["plan_completion_pct"] == 20


def test_the_sweep_never_creates_a_plan_or_reopens_a_decided_item(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, clock = plan_env
    _sweep(client, "sweep-no-plan")  # no plan exists today yet
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM daily_plans")) == 0

    clock.instant += timedelta(days=1)
    call(
        client,
        "POST",
        "/assessments",
        {**_python_warmup(client), "client_request_id": "warmup-first"},
        status=201,
    )
    items = today(client)["plan"]["items"]
    assert "BASE:M0-B01" not in [i["candidate_key"] for i in items]  # already complete, not re-planned
    target = next(i for i in items if i["status"] == "PENDING" and i["candidate_type"] == "BASELINE")
    skipped = call(client, "POST", f"/plan/items/{target['id']}/skip", {"skip_reason": "NO_TIME"})["data"]
    assert skipped["status"] == "SKIPPED"
    before = _plan_item_audits(catalog_engine)
    _record_battery(client, target["candidate_key"].removeprefix("BASE:"), "late-record")
    assert _item(client, target["candidate_key"])["status"] == "SKIPPED"  # only PENDING items are closed
    assert _plan_item_audits(catalog_engine) == before


def _python_warmup(client: TestClient) -> dict[str, Any]:
    return _battery_body(client, "M0-B03")


def _battery_body(client: TestClient, key: str) -> dict[str, Any]:
    battery = {i["key"]: i for i in call(client, "GET", "/baseline")["data"]["items"]}
    skills = [
        s["key"]
        for g in battery[key]["covers"]
        for s in call(client, "GET", f"/catalog/groups/{g}/skills")["data"]
    ]
    return {
        "kind": battery[key]["observation_kind"],
        "source_key": f"battery:{key}",
        "notes_used": False,
        "reference_used": False,
        "hints_used": 0,
        "timed": False,
        "skills": [{"skill": s, "outcome_points": 60} for s in skills[:4]],
        "battery_item_key": key,
        "mode": "BASELINE",
    }


def _record_battery(client: TestClient, key: str, request_id: str) -> dict[str, Any]:
    battery = {i["key"]: i for i in call(client, "GET", "/baseline")["data"]["items"]}
    if battery[key]["observation_kind"] == "ATTEMPT":
        body = {**SOLVED, "battery_item_key": key, "mode": "BASELINE", "client_request_id": request_id}
        return call(client, "POST", "/problem-attempts", body, status=201)["data"]
    body = {**_battery_body(client, key), "client_request_id": request_id}
    return call(client, "POST", "/assessments", body, status=201)["data"]


def test_battery_assessments_and_attempts_recorded_outside_the_plan_complete_their_items(
    plan_env: tuple[TestClient, MovableClock], catalog_engine: Engine
) -> None:
    client, clock = plan_env
    b02 = _item(client, "BASE:M0-B02")
    attempt = _record_battery(client, "M0-B02", "b02-own-page")
    item = _item(client, "BASE:M0-B02")
    assert (item["status"], item["observation_type"], item["observation_id"]) == (
        "DONE",
        "ATTEMPT",
        attempt["id"],
    )
    with sessionmaker(bind=catalog_engine)() as session:
        assert (
            session.scalar(text(f"SELECT plan_item_id FROM problem_attempts WHERE id = {attempt['id']}"))
            == b02["id"]
        )

    plain = call(
        client, "POST", "/problem-attempts", {**SOLVED, "client_request_id": "plain-attempt"}, status=201
    )["data"]
    assert plain["battery_item_key"] is None  # an ordinary attempt touches no plan item
    assert [s for _, s in _plan_item_audits(catalog_engine)] == ["COMPLETE_PLAN_ITEM"]

    clock.instant += timedelta(days=1)  # Monday: the next battery items are planned
    pending = next(
        i
        for i in today(client)["plan"]["items"]
        if i["candidate_type"] == "BASELINE"
        and i["status"] == "PENDING"
        and i["candidate_key"] != "BASE:M0-B01"
    )
    key = pending["candidate_key"].removeprefix("BASE:")
    recorded = _record_battery(client, key, "own-page")
    item = _item(client, pending["candidate_key"])
    assert (item["status"], item["observation_id"]) == ("DONE", recorded["id"])
    assert call(client, "GET", "/baseline")["data"]["items"][int(key[-2:]) - 1]["complete"] is True
