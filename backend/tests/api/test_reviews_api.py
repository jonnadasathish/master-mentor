"""Slice 11: weekly review generated lazily for a completed week, stored once, reflection audited."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog
from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db


def test_latest_review_covers_the_last_completed_week(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    # FIXED_NOW = 2026-10-04 (Sunday) -> the last completed week is 2026-09-21..27
    post(activity_client, "/problem-attempts", {**SOLVED, "attempted_at": "2026-09-23T06:00:00Z"})
    post(
        activity_client,
        "/problem-attempts",
        {**SOLVED, "problem_id": 27, "attempted_at": "2026-09-25T06:00:00Z"},
    )
    review = get(activity_client, "/weekly-reviews/latest")["data"]
    metrics = review["metrics"]
    assert (metrics["week_start"], metrics["week_end"], metrics["active_days"]) == (
        "2026-09-21",
        "2026-09-27",
        2,
    )
    assert metrics["readiness"]["start"]["state"] == "NOT_MEASURED"
    assert metrics["minutes_by_track"]["dsa_coding"]["minutes"] == 36  # 18 + 18 min attempts
    assert "dsa_coding" in review["next_focus"]["tracks_below_floor"]  # 36 < 105 (50% of 210)
    again = get(activity_client, "/weekly-reviews/2026-09-21")["data"]
    assert again["id"] == review["id"] and again["generated_at"] == review["generated_at"]  # stored once
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(AuditLog.action).where(AuditLog.action == "GENERATE_WEEKLY_REVIEW"))


def test_reflection_is_audited_and_unfinished_weeks_are_refused(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    get(activity_client, "/weekly-reviews/latest")
    body = post(
        activity_client,
        "/weekly-reviews/2026-09-21/reflection",
        {"improved": "graphs", "stop_doing": "re-reading"},
        status=200,
    )
    assert body["data"]["reflection"]["improved"] == "graphs" and body["data"]["reflected_at"]
    assert get(activity_client, "/weekly-reviews/2026-09-28", status=409)["error"]["code"] == "INVALID_STATE"
    assert (
        get(activity_client, "/weekly-reviews/2026-09-22", status=422)["error"]["code"] == "VALIDATION_ERROR"
    )
    post(activity_client, "/weekly-reviews/2026-08-03/reflection", {"improved": "x"}, status=404)
    assert get(activity_client, "/weekly-reviews")["meta"]["count"] == 1
    with sessionmaker(bind=catalog_engine)() as session:
        assert session.scalar(select(AuditLog.action).where(AuditLog.action == "REFLECT_WEEKLY_REVIEW"))
