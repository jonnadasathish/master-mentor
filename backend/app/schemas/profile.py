"""Settings and goal payloads."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SettingsOut(BaseModel):
    timezone: str
    display_name: str


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)


class GoalInput(BaseModel):
    """POST /goals (full) and PATCH /goals/active (fields not given are copied from the active version)."""

    model_config = ConfigDict(extra="forbid")

    target_date: date | None = None
    weekday_budgets: list[int] | None = Field(default=None, min_length=7, max_length=7)
    profile_key: str | None = Field(default=None, max_length=64)


class GoalPatch(GoalInput):
    clear_target_date: bool = False


class GoalOut(BaseModel):
    id: int
    profile_key: str
    target_date: date | None
    weekday_budgets: list[int]
    weekly_minutes: int
    valid_from: date
    valid_to: date | None
    is_active: bool
    created_at: datetime


class ActiveGoalOut(GoalOut):
    phase: str
    weeks_left: str | None  # one decimal, display only
