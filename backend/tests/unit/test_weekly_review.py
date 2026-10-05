"""MENTOR_ENGINE §10 weekly review metrics (pure, golden harness worlds)."""

from __future__ import annotations

from datetime import date

from app.domain.review.weekly import (
    WeekMockRound,
    WeekPlanItem,
    WeekPoint,
    generate_weekly_review,
    last_completed_week,
    week_bounds,
)
from tests.golden.harness import background, given, profile, readiness


def point(world, day: date, backlog: int = 0) -> WeekPoint:  # type: ignore[no-untyped-def]
    world.as_of = day
    return WeekPoint(day, dict(world.states), world.gaps(), readiness(world), backlog)


def test_week_bounds_and_last_completed_week() -> None:
    assert week_bounds(date(2026, 11, 4)) == (date(2026, 11, 2), date(2026, 11, 8))
    assert last_completed_week(date(2026, 11, 2)) == date(2026, 10, 26)  # Monday: last week just ended
    assert last_completed_week(date(2026, 11, 8)) == date(2026, 10, 26)


def test_metrics_completion_changes_readiness_and_focus() -> None:
    start_world = background()
    start_world.set(given("graph.traversal", 3, 51, "MEDIUM"))
    end_world = background()
    end_world.set(given("graph.traversal", 4, 66, "MEDIUM"))
    end_world.set(given("heap.top_k", 4, 70, "MEDIUM"))
    start, end = point(start_world, date(2026, 11, 1)), point(end_world, date(2026, 11, 8), backlog=35)
    items = [
        WeekPlanItem(date(2026, 11, 2), "GAP", 40, "DONE"),
        WeekPlanItem(date(2026, 11, 2), "REVISION", 25, "DONE"),
        WeekPlanItem(date(2026, 11, 3), "REVISION", 10, "SKIPPED"),
        WeekPlanItem(date(2026, 11, 3), "GAP", 50, "DISCARDED"),
        WeekPlanItem(date(2026, 11, 4), "FOLLOW_UP", 25, "PENDING"),
    ]
    tracks = {**profile().track_minutes, "system_design": 20}
    metrics, focus = generate_weekly_review(
        week_start=date(2026, 11, 2),
        start=start,
        end=end,
        active_days=4,
        plan_items=items,
        track_minutes=tracks,
        mock_rounds=[WeekMockRound(date(2026, 11, 7), "DSA", 76)],
        profile=profile(),
    )
    assert (metrics["planned_minutes"], metrics["completed_minutes"], metrics["plan_completion_pct"]) == (
        100,
        65,
        65,
    )
    assert metrics["revision_completion_pct"] == 50 and metrics["active_days"] == 4
    assert metrics["strongest_improvement"] == {
        "skill_key": "graph.traversal",
        "before": 44,
        "after": 59,
        "delta": 15,
    }
    assert metrics["biggest_regression"]["skill_key"] == "heap.top_k"  # 80 -> 63
    assert metrics["readiness"]["start"]["state"] == "DEVELOPING" and metrics["backlog_minutes"] == 35
    assert metrics["mocks"] == [{"date": "2026-11-07", "round_type": "DSA", "score": 76}]
    changes = {c["skill_key"]: c for c in metrics["gap_changes"]}
    assert changes["graph.traversal"]["delta"] < 0  # the gap shrank
    assert focus["tracks_below_floor"] == ["system_design"]
    assert [g["skill_key"] for g in focus["top_gaps"]][0] in ("heap.top_k", "graph.traversal")


def test_empty_week_has_no_rates() -> None:
    w = background()
    p = point(w, date(2026, 11, 8))
    metrics, _ = generate_weekly_review(
        week_start=date(2026, 11, 2),
        start=p,
        end=p,
        active_days=0,
        plan_items=[],
        track_minutes={},
        mock_rounds=[],
        profile=profile(),
    )
    assert (metrics["plan_completion_pct"], metrics["revision_completion_pct"]) == (None, None)
    assert metrics["strongest_improvement"] is None and metrics["biggest_regression"] is None
