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
