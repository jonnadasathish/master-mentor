# ruff: noqa: F811
"""Hybrid Today (D-086): once enough is measured the mentor plans one learning mission from the existing gap
engine next to the remaining battery; below the threshold it stays calibration-only; a complete battery keeps
the personalised plan. No scoring, readiness or evidence rule is involved."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.api.test_starting_profile_api import GOAL
from tests.api.test_today_api import MovableClock, call, plan_env, today  # noqa: F401

pytestmark = pytest.mark.db
LEARNING = ("GAP",)


def _sweep_unknown(client: TestClient, request_id: str = "sweep-hybrid") -> None:
    required = call(client, "GET", "/catalog/role-profile/targets?required=true")["data"]
    entries = [{"skill": t["skill"], "familiarity": "NONE"} for t in required]
    call(
        client,
        "POST",
        "/assessments/self-assessment-sweep",
        {"entries": entries, "client_request_id": request_id},
        status=201,
    )


def _next_day(client: TestClient, clock: MovableClock) -> dict[str, Any]:
    clock.instant += timedelta(days=1)  # Monday: a fresh plan is built from the evidence so far
    return today(client)


def _hybrid_day(client: TestClient, clock: MovableClock) -> dict[str, Any]:
    call(client, "POST", "/goals", GOAL, status=201)
    _sweep_unknown(client)
    assert call(client, "GET", "/baseline")["data"]["phase"] == "ENOUGH_MEASURED"
    return _next_day(client, clock)


def _types(plan: dict[str, Any]) -> list[str]:
    return [i["candidate_type"] for i in plan["items"]]


def test_below_the_threshold_calibration_stays_primary(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, _ = plan_env
    call(client, "POST", "/goals", GOAL, status=201)
    data = today(client)
    assert call(client, "GET", "/baseline")["data"]["phase"] == "NOT_STARTED"
    assert set(_types(data["plan"])) == {"BASELINE"}  # nothing invented
    assert data["plan"]["message"]["rule"] == "CALIBRATION" and data["plan"]["learning"] == {}


def test_enough_evidence_with_an_open_battery_offers_one_learning_mission_first(
    plan_env: tuple[TestClient, MovableClock],
) -> None:
    client, clock = plan_env
    data = _hybrid_day(client, clock)
    plan = data["plan"]
    types = _types(plan)
    assert data["calibration"]["active"] is True and data["calibration"]["battery_done"] == 1  # still open
    assert types.count("GAP") == 1 and "BASELINE" in types, types
    assert types.index("GAP") < types.index("BASELINE")  # learning is the primary action
    assert plan["message"]["rule"] != "CALIBRATION"  # "No new material until..." no longer true
    gap = next(i for i in plan["items"] if i["candidate_type"] == "GAP")
    assert gap["skill"] and gap["explanation"] and gap["minutes"] > 0
    assert plan["allocated_minutes"] <= plan["budget_minutes"]
    keys = [i["candidate_key"] for i in plan["items"]]
    assert len(keys) == len(set(keys))  # no duplicate plan item


def test_the_hybrid_plan_is_deterministic(
    plan_env: tuple[TestClient, MovableClock],
    catalog_engine: Engine,
) -> None:
    client, clock = plan_env
    first = _hybrid_day(client, clock)["plan"]
    with catalog_engine.begin() as connection:
        hash_before = connection.execute(text("SELECT input_hash FROM daily_plans ORDER BY id DESC")).scalar()
        connection.execute(text("DELETE FROM plan_items WHERE plan_id = :p"), {"p": first["id"]})
        connection.execute(text("DELETE FROM daily_plans WHERE id = :p"), {"p": first["id"]})
    second = today(client)["plan"]
    strip = lambda items: [{k: v for k, v in i.items() if k != "id"} for i in items]  # noqa: E731
    assert strip(second["items"]) == strip(first["items"]) and second["message"] == first["message"]
    with catalog_engine.connect() as connection:
        hash_after = connection.execute(text("SELECT input_hash FROM daily_plans ORDER BY id DESC")).scalar()
        assert hash_after == hash_before


def test_replanning_keeps_done_work_and_never_duplicates(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, clock = plan_env
    plan = _hybrid_day(client, clock)["plan"]
    gap = next(i for i in plan["items"] if i["candidate_type"] == "GAP")
    base = next(i for i in plan["items"] if i["candidate_type"] == "BASELINE")
    call(client, "POST", f"/plan/items/{base['id']}/complete", {"no_evidence": True})
    again = call(client, "POST", "/plan/today/regenerate")["data"]["plan"]
    keys = [i["candidate_key"] for i in again["items"] if i["status"] != "DISCARDED"]
    assert len(keys) == len(set(keys))
    by_key = {i["candidate_key"]: i for i in again["items"]}
    kept = by_key[base["candidate_key"]]
    assert (kept["status"], kept["id"]) == ("DONE", base["id"])
    assert by_key[gap["candidate_key"]]["status"] == "PENDING"  # the same mission, still pending


def test_a_frozen_pre_threshold_plan_can_be_replanned_into_a_hybrid_one(
    plan_env: tuple[TestClient, MovableClock],
) -> None:
    client, _ = plan_env
    call(client, "POST", "/goals", GOAL, status=201)
    assert set(_types(today(client)["plan"])) == {"BASELINE"}  # frozen calibration-only plan
    _sweep_unknown(client)
    assert set(_types(today(client)["plan"])) == {"BASELINE"}  # plans never change under you
    replanned = call(client, "POST", "/plan/today/regenerate")["data"]["plan"]
    assert "GAP" in _types(replanned)


def test_starting_the_learning_mission_links_the_session_to_its_plan_item(
    plan_env: tuple[TestClient, MovableClock],
) -> None:
    client, clock = plan_env
    plan = _hybrid_day(client, clock)["plan"]
    gap = next(i for i in plan["items"] if i["candidate_type"] == "GAP")
    preview = plan["learning"].get(str(gap["id"]))
    if preview is None:
        pytest.skip("the library has no session for today's top gap")
    started = call(
        client,
        "POST",
        "/learning/sessions",
        {"skill": gap["skill"], "stage": preview["stage"], "plan_item_id": gap["id"]},
        status=201,
    )["data"]
    assert started["plan_item_id"] == gap["id"] and started["status"] == "ACTIVE"
    after = today(client)["plan"]
    assert after["learning"][str(gap["id"])]["session_id"] == started["id"]
    assert [i["id"] for i in after["items"]] == [i["id"] for i in plan["items"]]  # nothing created or removed


def test_the_remaining_battery_still_completes_and_finishes_calibration(
    plan_env: tuple[TestClient, MovableClock],
) -> None:
    client, clock = plan_env
    plan = _hybrid_day(client, clock)["plan"]
    base = next(i for i in plan["items"] if i["candidate_type"] == "BASELINE")
    done = call(client, "POST", f"/plan/items/{base['id']}/complete", {"no_evidence": True})
    assert done["data"]["item"]["status"] == "DONE"
    assert call(client, "GET", "/baseline")["data"]["battery_done"] == 2


def test_a_complete_battery_keeps_the_personalised_plan(plan_env: tuple[TestClient, MovableClock]) -> None:
    client, clock = plan_env
    _hybrid_day(client, clock)
    for _ in range(10):  # work through the battery by completing each day's baseline items
        plan = today(client)["plan"]
        for item in plan["items"]:
            if item["candidate_type"] == "BASELINE" and item["status"] == "PENDING":
                call(client, "POST", f"/plan/items/{item['id']}/complete", {"no_evidence": True})
        if call(client, "GET", "/baseline")["data"]["phase"] == "COMPLETE":
            break
        clock.instant += timedelta(days=1)
    baseline = call(client, "GET", "/baseline")["data"]
    assert baseline["phase"] == "COMPLETE"
    clock.instant += timedelta(days=1)
    final = today(client)["plan"]
    assert "GAP" in _types(final) and "BASELINE" not in _types(final)
