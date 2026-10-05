"""Weekly review payloads. Reflection is free text that no engine ever reads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

Text = Field(default="", max_length=2000)


class ReflectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    improved: str = Text
    still_weak: str = Text
    failure_causes: str = Text
    stop_doing: str = Text
    next_priority: str = Text


class WeeklyReviewOut(BaseModel):
    id: int
    week_start: date
    run_id: int | None
    ruleset_version: str
    metrics: dict[str, Any]
    next_focus: dict[str, Any]
    reflection: dict[str, Any] | None
    generated_at: datetime
    reflected_at: datetime | None
