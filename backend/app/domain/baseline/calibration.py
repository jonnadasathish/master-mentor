"""Cold start: baseline battery progress and Calibration Mode (MENTOR_ENGINE.md §2, "Calibration Mode").

``calibration_mode := battery incomplete OR assessed required skills < CALIBRATION_MIN_ASSESSED_PCT``.
A skill is *assessed* when its confidence is not NONE (declared-unknown skills are assessed at 0); callers
pass the assessed skill keys (``SkillState.assessed``). Pure: everything is passed in.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from types import ModuleType


@dataclass(frozen=True)
class BatteryItemStatus:
    key: str
    position: int
    name: str
    minutes: int
    observation_kind: str
    covers: tuple[str, ...]
    complete: bool


@dataclass(frozen=True)
class CalibrationStatus:
    items: tuple[BatteryItemStatus, ...]
    battery_complete: bool
    battery_done: int
    battery_total: int
    next_item: str | None
    required: int
    assessed_required: int
    assessed_pct: int  # floor
    calibration_mode: bool


@dataclass(frozen=True)
class BatteryItem:
    key: str
    position: int
    name: str
    minutes: int
    observation_kind: str
    covers: tuple[str, ...]


def calibration_status(
    *,
    battery: Sequence[BatteryItem],
    completed_keys: set[str],
    required_skills: Sequence[str],
    assessed_skills: Collection[str],
    ruleset: ModuleType,
) -> CalibrationStatus:
    ordered = sorted(battery, key=lambda b: (b.position, b.key))
    items = tuple(
        BatteryItemStatus(
            b.key, b.position, b.name, b.minutes, b.observation_kind, b.covers, b.key in completed_keys
        )
        for b in ordered
    )
    done = sum(1 for i in items if i.complete)
    required = len(required_skills)
    assessed = sum(1 for k in required_skills if k in assessed_skills)
    pct = assessed * 100 // required if required else 0
    complete = done == len(items)
    return CalibrationStatus(
        items=items,
        battery_complete=complete,
        battery_done=done,
        battery_total=len(items),
        next_item=next((i.key for i in items if not i.complete), None),
        required=required,
        assessed_required=assessed,
        assessed_pct=pct,
        calibration_mode=(not complete) or pct < int(ruleset.CALIBRATION_MIN_ASSESSED_PCT),
    )


# ------------------------------------------------------------------------------ calibration phase (UX status)
# NOT_STARTED: no battery item done and no required skill assessed yet.
# COMPLETE: every battery item is done (the mentor then plans from the gap engine as usual).
# ENOUGH_MEASURED: the battery is still open but at least CALIBRATION_MIN_ASSESSED_PCT of the required
#   skills are assessed, i.e. a first personal roadmap can already be read from the engines (the mentor keeps
#   scheduling the rest of the battery; its rules are unchanged).
# IN_PROGRESS: everything else.
PHASES = ("NOT_STARTED", "IN_PROGRESS", "ENOUGH_MEASURED", "COMPLETE")


def calibration_phase(status: CalibrationStatus, ruleset: ModuleType) -> str:
    if status.battery_complete:
        return "COMPLETE"
    if status.battery_done == 0 and status.assessed_required == 0:
        return "NOT_STARTED"
    if status.assessed_pct >= int(ruleset.CALIBRATION_MIN_ASSESSED_PCT):
        return "ENOUGH_MEASURED"
    return "IN_PROGRESS"


@dataclass(frozen=True)
class BaselineEffort:
    minutes_total: int
    minutes_done: int
    minutes_remaining: int
    typical_daily_minutes: int | None  # average of the goal's non-zero weekday budgets; None without a goal
    estimated_days: int | None  # whole days at that pace (rounded up); None without a goal


def typical_daily_minutes(weekday_budgets: Sequence[int]) -> int | None:
    days = [b for b in weekday_budgets if b > 0]
    return sum(days) // len(days) if days else None


def baseline_effort(status: CalibrationStatus, weekday_budgets: Sequence[int] | None) -> BaselineEffort:
    """Total/done/remaining battery minutes and a rough day count. The mentor, not this estimate, decides each
    day's diagnostic work (MENTOR_ENGINE §3); this only tells the user how long the baseline will take."""
    total = sum(i.minutes for i in status.items)
    done = sum(i.minutes for i in status.items if i.complete)
    remaining = total - done
    typical = typical_daily_minutes(weekday_budgets) if weekday_budgets else None
    days = None if not typical else (remaining + typical - 1) // typical
    return BaselineEffort(total, done, remaining, typical, days)
