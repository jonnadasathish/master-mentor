"""Goal versioning rules (DATA_MODEL §3, D-033). Pure."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

WEEKDAYS = 7
MIN_DAILY_MINUTES = 0
MAX_DAILY_MINUTES = 600


@dataclass(frozen=True)
class GoalFieldError:
    field: str
    message: str


def goal_errors(
    *, target_date: date | None, weekday_budgets: Sequence[int], today: date
) -> list[GoalFieldError]:
    errors: list[GoalFieldError] = []
    if len(weekday_budgets) != WEEKDAYS:
        errors.append(GoalFieldError("weekday_budgets", "exactly 7 values, Monday to Sunday"))
    elif any(b < MIN_DAILY_MINUTES or b > MAX_DAILY_MINUTES for b in weekday_budgets):
        errors.append(GoalFieldError("weekday_budgets", f"each day 0-{MAX_DAILY_MINUTES} minutes"))
    elif sum(weekday_budgets) == 0:
        errors.append(GoalFieldError("weekday_budgets", "at least one day needs minutes"))
    if target_date is not None and target_date <= today:
        errors.append(GoalFieldError("target_date", "must be after today"))
    return errors


def budget_for(weekday_budgets: Sequence[int], day: date) -> int:
    """Daily budget B for a local date (Monday = index 0)."""
    return int(weekday_budgets[day.weekday()])
