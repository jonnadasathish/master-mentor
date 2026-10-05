"""Mock interview / final simulation payloads (raw observations)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoundType = Literal["DSA", "CS", "LLD", "SYSTEM_DESIGN", "BEHAVIORAL", "PROJECT_DEEP_DIVE"]
Points = Field(ge=0, le=100)


class MockRoundSkillIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=64)
    outcome_points: int = Points
    is_weakness: bool = False


class MockRoundIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_type: RoundType
    duration_minutes: int = Field(ge=1, le=240)
    round_score: int = Points
    communication_points: int | None = Field(default=None, ge=0, le=100)
    rubric: dict[str, int] | None = Field(default=None, max_length=20)
    skills: list[MockRoundSkillIn] = Field(default_factory=list, max_length=20)


class MockInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_at: datetime | None = None
    source: Literal["SELF", "PEER", "PLATFORM"]
    is_final_simulation: bool = False
    notes: str | None = Field(default=None, max_length=4000)
    rounds: list[MockRoundIn] = Field(min_length=1, max_length=8)
    client_request_id: str | None = Field(default=None, min_length=8, max_length=64)

    @field_validator("occurred_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("must include a timezone offset (e.g. 2026-10-04T18:30:00Z)")
        return value


class MockRoundOut(MockRoundIn):
    id: int
    position: int


class MockOut(BaseModel):
    id: int
    occurred_on: date
    occurred_at: datetime
    source: str
    is_final_simulation: bool
    notes: str | None
    rounds: list[MockRoundOut]
    supersedes_id: int | None
    superseded_by_id: int | None
    is_current: bool
