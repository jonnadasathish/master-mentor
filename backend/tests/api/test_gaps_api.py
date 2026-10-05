"""Slice 5 behavior through the API: settings, versioned goals, gaps, write effects with gap deltas."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog, MentorRun
from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db


def patch(client: TestClient, path: str, body: dict[str, Any], status: int = 200) -> dict[str, Any]:
    response = client.patch(f"/api/v1{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


# ------------------------------------------------------------------------------- settings


def test_settings_read_and_update_is_audited(activity_client: TestClient, catalog_engine: Engine) -> None:
    before = get(activity_client, "/settings")["data"]
    assert set(before) == {"timezone", "display_name"}
    body = patch(activity_client, "/settings", {"display_name": "Satish", "timezone": "Europe/Berlin"})
    assert body["data"] == {"timezone": "Europe/Berlin", "display_name": "Satish"}
    assert "effects" in body
    bad = patch(activity_client, "/settings", {"timezone": "Mars/Base"}, status=422)
    assert bad["error"]["details"]["errors"][0]["loc"] == ["body", "timezone"]
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(AuditLog.action).where(AuditLog.action == "UPDATE_SETTINGS"))


# ------------------------------------------------------------------------------- goals


def test_goal_lifecycle_versions_never_overwrite(activity_client: TestClient, catalog_engine: Engine) -> None:
    get(activity_client, "/goals/active", status=404)
    created = post(activity_client, "/goals", {"target_date": "2027-06-28"})["data"]
    assert created["weekday_budgets"] == [90, 90, 90, 90, 90, 75, 75] and created["weekly_minutes"] == 600
    assert (created["valid_from"], created["valid_to"], created["is_active"]) == ("2026-10-04", None, True)
    active = get(activity_client, "/goals/active")["data"]
    assert (active["phase"], active["weeks_left"], active["profile_key"]) == (
        "BUILD",
        "38.1",
        "backend_fullstack_sde2",
    )

    changed = patch(activity_client, "/goals/active", {"weekday_budgets": [60, 60, 60, 60, 60, 120, 120]})
    assert changed["data"]["target_date"] == "2027-06-28" and changed["data"]["id"] != created["id"]
    history = get(activity_client, "/goals/history")["data"]
    assert [g["is_active"] for g in history] == [False, True]
    assert history[0]["valid_to"] == "2026-10-04" and history[0]["weekday_budgets"][0] == 90  # old row kept

    near = patch(activity_client, "/goals/active", {"target_date": "2026-10-25"})["data"]
    assert (
        get(activity_client, "/goals/active")["data"]["phase"] == "SHARPEN"
        and near["weekday_budgets"][0] == 60
    )
    with sessionmaker(bind=catalog_engine)() as session:
        actions = session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "goal")).all()
        assert sorted(actions) == ["CHANGE_GOAL", "CHANGE_GOAL", "CREATE_GOAL"]
        run = session.scalars(select(MentorRun).order_by(MentorRun.id.desc())).first()
        assert run is not None and run.phase is not None and run.phase.value == "SHARPEN"
        assert run.calibration_mode is True and run.goal_id == near["id"]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"target_date": "2026-10-04"}, "target_date"),
        ({"weekday_budgets": [90, 90, 90, 90, 90, 75]}, "weekday_budgets"),
        ({"weekday_budgets": [0, 0, 0, 0, 0, 0, 0]}, "weekday_budgets"),
        ({"weekday_budgets": [90, 90, 90, 90, 90, 75, 700]}, "weekday_budgets"),
    ],
)
def test_goal_validation(activity_client: TestClient, body: dict[str, Any], field: str) -> None:
    error = post(activity_client, "/goals", body, status=422)["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in str(error["details"])


def test_unknown_profile_is_404(activity_client: TestClient) -> None:
    post(activity_client, "/goals", {"profile_key": "nope"}, status=404)


# ------------------------------------------------------------------------------- gaps


def test_cold_start_gaps_are_unassessed_and_blocked(activity_client: TestClient) -> None:
    post(activity_client, "/goals", {"target_date": "2027-06-28"})
    body = get(activity_client, "/gaps")
    report = body["data"]
    assert (report["phase"], report["weeks_left"], report["calibration_mode"]) == ("BUILD", "38.1", True)
    assert body["meta"]["count"] == 133 and body["meta"]["run_id"] >= 1
    statuses = [g["status"] for g in report["gaps"]]
    assert statuses.count("UNASSESSED") == 31 and statuses.count("BLOCKED") == 102
    first = report["gaps"][0]
    assert (first["skill_key"], first["priority"], first["rank"]) == ("behavioral.impact", 100, 1)
    assert first["recommended_focus"] == {"stage": "DIAGNOSE", "focus_skill": "behavioral.impact"}
    response = activity_client.get(
        "/api/v1/gaps", params={"status": "BLOCKED", "component": "dsa", "limit": 3}
    )
    limited = response.json()["data"]["gaps"]
    assert len(limited) == 3 and {g["status"] for g in limited} == {"BLOCKED"}


def test_evidence_moves_a_gap_and_reports_gap_deltas(activity_client: TestClient) -> None:
    post(activity_client, "/goals", {"target_date": "2027-06-28"})
    get(activity_client, "/gaps")  # establish the baseline run
    body = post(
        activity_client, "/problem-attempts", {**SOLVED, "outcome": "FAIL", "mistakes": ["WRONG_PATTERN"]}
    )
    deltas = {d["skill_key"]: d for d in body["effects"]["gap_deltas"]}
    assert deltas, body["effects"]
    changed = next(iter(deltas.values()))
    assert changed["before"]["status"] in ("UNASSESSED", "BLOCKED") and changed["after"] != changed["before"]
    key = changed["skill_key"]
    detail = get(activity_client, f"/gaps/{key}")["data"]
    assert detail["skill_key"] == key and detail["status"] == changed["after"]["status"]
    assert "SKILL_STATE" in detail["evidence"]
    assert detail["evidence"]["SKILL_STATE"][0]["source_type"] == "ATTEMPT"


def test_gap_detail_unknown_skill_404(activity_client: TestClient) -> None:
    get(activity_client, "/gaps/no.such", status=404)


def test_gaps_without_goal_still_rank_in_build_phase(activity_client: TestClient) -> None:
    report = get(activity_client, "/gaps", limit=1)["data"]
    assert (report["phase"], report["weeks_left"], report["calibration_mode"]) == ("BUILD", None, None)
