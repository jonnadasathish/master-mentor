"""Cold start: battery progress and Calibration Mode (MENTOR_ENGINE.md §2)."""

from __future__ import annotations

from app.domain.baseline.calibration import BatteryItem, calibration_status
from app.domain.rulesets import v1

BATTERY = [BatteryItem(f"M0-B{i:02d}", i, f"item {i}", 20, "ATTEMPT", ("x",)) for i in (3, 1, 2)]
REQUIRED = [f"s.{i}" for i in range(10)]


def status(done: set[str], assessed: set[str]):  # type: ignore[no-untyped-def]
    return calibration_status(
        battery=BATTERY, completed_keys=done, required_skills=REQUIRED, assessed_skills=assessed, ruleset=v1
    )


def test_items_are_in_battery_order_and_next_item_is_first_pending() -> None:
    s = status({"M0-B01"}, set())
    assert [i.key for i in s.items] == ["M0-B01", "M0-B02", "M0-B03"]
    assert (s.battery_done, s.next_item, s.calibration_mode) == (1, "M0-B02", True)


def test_complete_battery_but_under_60_percent_assessed_stays_in_calibration() -> None:
    s = status({"M0-B01", "M0-B02", "M0-B03"}, {f"s.{i}" for i in range(5)})
    assert (s.battery_complete, s.assessed_pct, s.calibration_mode) == (True, 50, True)


def test_exit_needs_battery_and_60_percent() -> None:
    assert status({"M0-B01", "M0-B02", "M0-B03"}, {f"s.{i}" for i in range(6)}).calibration_mode is False
    # 100% assessed but battery incomplete: still calibrating (no premature feasibility).
    assert status({"M0-B01"}, set(REQUIRED)).calibration_mode is True


def test_non_required_assessed_skills_do_not_count() -> None:
    assert status(set(), {"other.skill"}).assessed_required == 0
