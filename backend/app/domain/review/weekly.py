"""Weekly review (MENTOR_ENGINE.md §10). Pure: two engine evaluations (entering the week and at its end) plus
the week's plan items, practice minutes and mock rounds in; metrics out. No clock, no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.domain.gaps.model import GapReport
from app.domain.profile.model import ProfileSpec
from app.domain.readiness.engine import Readiness
from app.domain.skills.state import SkillState

TOP_GAPS = 5
NEXT_FOCUS_GAPS = 3
TRACK_FLOOR_PCT = 50


@dataclass(frozen=True)
class WeekPoint:
    """The engine view at one date (states, gaps, readiness, revision backlog)."""

    as_of: date
    states: Mapping[str, SkillState]
    gaps: GapReport
    readiness: Readiness
    backlog_minutes: int


@dataclass(frozen=True)
class WeekPlanItem:
    plan_date: date
    candidate_type: str
    minutes: int
    status: str


@dataclass(frozen=True)
class WeekMockRound:
    occurred_on: date
    round_type: str
    score: int


def week_bounds(any_day: date) -> tuple[date, date]:
    """Monday..Sunday (local) of the week containing ``any_day``."""
    start = any_day - timedelta(days=any_day.weekday())
    return start, start + timedelta(days=6)


def last_completed_week(today: date) -> date:
    """Monday of the most recent week that has fully ended before ``today``."""
    this_monday, _ = week_bounds(today)
    return this_monday - timedelta(days=7)


def _actionable(report: GapReport, n: int) -> list[dict[str, Any]]:
    return [
        {
            "skill_key": g.skill_key,
            "status": g.status,
            "priority": g.priority,
            "primary_gap_type": g.primary_gap_type,
        }
        for g in report.top_assessed(n)
    ]


def generate_weekly_review(
    *,
    week_start: date,
    start: WeekPoint,
    end: WeekPoint,
    active_days: int,
    plan_items: Sequence[WeekPlanItem],
    track_minutes: Mapping[str, int],
    mock_rounds: Sequence[WeekMockRound],
    profile: ProfileSpec,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (metrics, next_week_focus)."""
    planned = [i for i in plan_items if i.status != "DISCARDED"]
    planned_minutes = sum(i.minutes for i in planned)
    completed_minutes = sum(i.minutes for i in planned if i.status == "DONE")
    revisions = [i for i in planned if i.candidate_type == "REVISION"]
    reviews_done = sum(1 for i in revisions if i.status == "DONE")

    top_start = {g["skill_key"]: g for g in _actionable(start.gaps, TOP_GAPS)}
    top_end = _actionable(end.gaps, TOP_GAPS)
    start_gaps, end_gaps = start.gaps.by_skill(), end.gaps.by_skill()
    gap_changes = []
    for key in sorted({*top_start, *(g["skill_key"] for g in top_end)}):
        before = start_gaps.get(key)
        after = end_gaps.get(key)
        gap_changes.append(
            {
                "skill_key": key,
                "before": before.priority if before else None,
                "after": after.priority if after else None,
                "delta": (after.priority if after else 0) - (before.priority if before else 0),
            }
        )

    deltas = []
    for key, s_end in end.states.items():
        s_start = start.states.get(key)
        a = s_end.effective_score
        b = s_start.effective_score if s_start is not None else None
        if a is not None and b is not None and a != b:
            deltas.append((a - b, key, b, a))
    improvement = max(deltas, key=lambda d: (d[0], d[1]), default=None)
    regression = min(deltas, key=lambda d: (d[0], d[1]), default=None)

    def change(d: tuple[int, str, int, int] | None, positive: bool) -> dict[str, Any] | None:
        if d is None or (d[0] <= 0 if positive else d[0] >= 0):
            return None
        return {"skill_key": d[1], "before": d[2], "after": d[3], "delta": d[0]}

    start_blockers = [c.message for c in start.readiness.blockers]
    end_blockers = [c.message for c in end.readiness.blockers]
    by_track = {
        track: {"minutes": track_minutes.get(track, 0), "weekly_target": minutes}
        for track, minutes in profile.track_minutes.items()
    }
    metrics: dict[str, Any] = {
        "week_start": week_start.isoformat(),
        "week_end": (week_start + timedelta(days=6)).isoformat(),
        "active_days": active_days,
        "planned_minutes": planned_minutes,
        "completed_minutes": completed_minutes,
        "plan_completion_pct": completed_minutes * 100 // planned_minutes if planned_minutes else None,
        "revision_completion_pct": reviews_done * 100 // len(revisions) if revisions else None,
        "minutes_by_track": by_track,
        "top_gaps": top_end,
        "gap_changes": gap_changes,
        "strongest_improvement": change(improvement, True),
        "biggest_regression": change(regression, False),
        "readiness": {
            "start": {"state": start.readiness.state, "weighted_score": start.readiness.weighted_score},
            "end": {"state": end.readiness.state, "weighted_score": end.readiness.weighted_score},
            "new_blockers": [b for b in end_blockers if b not in start_blockers],
            "cleared_blockers": [b for b in start_blockers if b not in end_blockers],
        },
        "mocks": [
            {"date": r.occurred_on.isoformat(), "round_type": r.round_type, "score": r.score}
            for r in sorted(mock_rounds, key=lambda r: (r.occurred_on, r.round_type))
        ],
        "backlog_minutes": end.backlog_minutes,
    }
    next_focus = {
        "top_gaps": _actionable(end.gaps, NEXT_FOCUS_GAPS),
        "tracks_below_floor": sorted(
            t
            for t, v in by_track.items()
            if t != "mock" and v["minutes"] * 100 < v["weekly_target"] * TRACK_FLOOR_PCT
        ),
        "stop_list": sorted(
            {
                g.skill_key
                for g in end.gaps.gaps
                if g.status == "PARKED" or "STUDIED_NOT_TESTED" in g.reason_codes
            }
        ),
    }
    return metrics, next_focus
