"""Calibration phase and baseline effort (D-080): the user-facing status of the baseline. Pure."""

from __future__ import annotations

from app.domain.baseline.calibration import (
    BatteryItem,
    baseline_effort,
    calibration_phase,
    calibration_status,
    typical_daily_minutes,
)
from app.domain.rulesets import v1

BATTERY = tuple(
    BatteryItem(f"M0-B{i:02d}", i, f"Item {i}", minutes, "ATTEMPT", ("g",))
    for i, minutes in enumerate((15, 60, 30, 20), start=1)
)  # 4 items, 125 minutes
REQUIRED = [f"s{i}" for i in range(10)]


def status(done: int, assessed: int):  # type: ignore[no-untyped-def]
    return calibration_status(
        battery=BATTERY,
        completed_keys={b.key for b in BATTERY[:done]},
        required_skills=REQUIRED,
        assessed_skills=set(REQUIRED[:assessed]),
        ruleset=v1,
    )


def test_not_started_without_any_evidence() -> None:
    assert calibration_phase(status(0, 0), v1) == "NOT_STARTED"


def test_in_progress_after_some_work_below_the_threshold() -> None:
    assert calibration_phase(status(1, 3), v1) == "IN_PROGRESS"  # 30% of required assessed
    assert calibration_phase(status(0, 1), v1) == "IN_PROGRESS"  # a declared unknown counts as evidence


def test_enough_measured_at_the_personalization_threshold_while_the_battery_is_open() -> None:
    assert v1.CALIBRATION_MIN_ASSESSED_PCT == 60  # the existing rule; this change does not alter it
    assert calibration_phase(status(2, 5), v1) == "IN_PROGRESS"  # 50%
    assert calibration_phase(status(2, 6), v1) == "ENOUGH_MEASURED"  # 60%
    assert status(2, 6).calibration_mode is True  # the mentor still schedules the rest of the battery


def test_complete_when_every_item_is_done_whatever_was_assessed() -> None:
    assert calibration_phase(status(4, 10), v1) == "COMPLETE"
    assert calibration_phase(status(4, 2), v1) == "COMPLETE"


def test_effort_counts_minutes_done_and_remaining() -> None:
    effort = baseline_effort(status(2, 5), [90, 90, 90, 90, 90, 75, 75])
    assert (effort.minutes_total, effort.minutes_done, effort.minutes_remaining) == (125, 75, 50)
    assert effort.typical_daily_minutes == 85  # average of the seven non-zero budgets, floored
    assert effort.estimated_days == 1
    assert (
        baseline_effort(status(0, 0), [90, 90, 90, 90, 90, 75, 75]).estimated_days == 2
    )  # 125 / 85, rounded up


def test_effort_ignores_days_off_and_needs_a_goal_for_an_estimate() -> None:
    assert typical_daily_minutes([60, 60, 0, 0, 0, 0, 0]) == 60
    assert typical_daily_minutes([0] * 7) is None
    effort = baseline_effort(status(0, 0), None)
    assert (effort.typical_daily_minutes, effort.estimated_days, effort.minutes_remaining) == (
        None,
        None,
        125,
    )
