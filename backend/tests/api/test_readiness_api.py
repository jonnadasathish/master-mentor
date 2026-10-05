"""Slice 8 behavior through the API: readiness object, history, Today header, rebuild reproducibility."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db


def test_cold_start_readiness_is_not_measured(activity_client: TestClient) -> None:
    body = get(activity_client, "/readiness")
    data = body["data"]
    assert (data["state"], data["simulation_eligible"], data["lapsed"]) == ("NOT_MEASURED", False, False)
    assert [g["gate"] for g in data["gates"]] == [f"G{i}" for i in range(10)]
    assert {b["gate"] for b in data["blockers"]} == {"G0"} and len(data["blockers"]) == 7
    assert data["blockers"][0]["message"].endswith("assessed 0% < 70%")
    assert len(data["components"]) == 7 and body["meta"]["run_id"] >= 1
    assert {c["gate"] for c in data["all_failing"]} >= {"G0", "G1", "G2", "G6", "G9"}


def test_history_lists_daily_snapshots(activity_client: TestClient) -> None:
    get(activity_client, "/readiness")
    history = get(activity_client, "/readiness/history")
    assert history["meta"]["count"] == 1
    item = history["data"][0]
    assert (item["date"], item["state"]) == ("2026-10-04", "NOT_MEASURED") and set(item["components"]) >= {
        "dsa",
        "cs",
    }


def test_today_header_and_mentor_read_the_same_readiness(activity_client: TestClient) -> None:
    post(activity_client, "/goals", {"target_date": "2027-06-28"})
    today = get(activity_client, "/today")["data"]
    assert today["readiness"]["state"] == "NOT_MEASURED"
    assert today["readiness"]["blockers"][0]["gate"] == "G0"


def test_rebuild_reproduces_readiness(activity_client: TestClient, catalog_engine: Engine) -> None:
    post(activity_client, "/problem-attempts", SOLVED)
    get(activity_client, "/readiness")

    def snap() -> list[tuple[object, ...]]:
        with catalog_engine.connect() as c:
            rows = c.execute(
                text(
                    "SELECT snapshot_date, state, weighted_score, gates_json, blockers_json "
                    "FROM readiness_snapshots"
                )
            ).all()
        return [tuple(r) for r in rows]

    before = snap()
    post(activity_client, "/admin/rebuild", {}, status=200)
    assert snap() == before
