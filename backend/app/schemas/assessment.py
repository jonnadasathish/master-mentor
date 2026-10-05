"""Assessment payloads (raw observations of non-problem practice). Nothing here is a score."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.activity import vocabulary as av
from app.schemas.activity import AttemptMode, Difficulty

AssessmentKind = Literal[
    "STUDY_SESSION",
    "SELF_ASSESSMENT",
    "RECALL_QUIZ",
    "PATTERN_DRILL",
    "CONCEPT_EXPLAIN",
    "CODE_EXERCISE",
    "ESTIMATION_DRILL",
    "SD_DESIGN",
    "LLD_DESIGN",
    "MACHINE_CODING",
    "STORY_REHEARSAL",
    "PROJECT_WALKTHROUGH",
    "APPLIED_TASK",
]
Familiarity = Literal["NONE", "SOME", "SOLID"]
Points = Field(default=None, ge=0, le=100)
Rating = Field(default=None, ge=av.SELF_RATING_MIN, le=av.SELF_RATING_MAX)


class AssessmentSkillIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=64)
    outcome_points: int | None = Points
    mapping_weight_bp: Literal[5000, 10000] = 10000
    is_pattern_target: bool = False


class AssessmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: AssessmentKind
    observed_at: datetime | None = None  # UTC-aware instant; defaults to "now" on the server
    mode: AttemptMode = "PRACTICE"
    source_key: str = Field(min_length=1, max_length=96)  # prompt:<key>, exercise:<key>, story:<id>, ...
    notes_used: bool = False
    reference_used: bool = False
    hints_used: int = Field(default=0, ge=0, le=av.MAX_HINTS)
    timed: bool = False
    time_limit_seconds: int | None = Field(default=None, ge=av.MIN_TIME_LIMIT_SECONDS, le=av.MAX_SECONDS)
    time_seconds: int | None = Field(default=None, ge=0, le=av.MAX_SECONDS)
    peer_evaluated: bool = False
    applied: bool = False
    unseen_variant: bool = False
    difficulty: Difficulty = "MEDIUM"
    followup_points: int | None = Points
    communication_points: int | None = Points
    rubric: dict[str, int] | None = Field(default=None, max_length=20)
    familiarity: Familiarity | None = None
    study_minutes: int | None = Field(default=None, ge=1, le=av.MAX_STUDY_MINUTES)
    skills: list[AssessmentSkillIn] = Field(min_length=1, max_length=av.MAX_ASSESSMENT_SKILLS)
    self_rating_before: int | None = Rating
    self_rating_after: int | None = Rating
    notes: str | None = Field(default=None, max_length=av.MAX_NOTES_CHARS)
    revision_item_key: str | None = Field(default=None, max_length=96)
    battery_item_key: str | None = Field(default=None, max_length=16)
    client_request_id: str | None = Field(default=None, min_length=8, max_length=64)

    @field_validator("observed_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("must include a timezone offset (e.g. 2026-10-04T18:30:00Z)")
        return value


class SweepEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=64)
    familiarity: Familiarity


class SelfAssessmentSweepInput(BaseModel):
    """Battery item M0-B01: one SELF_ASSESSMENT per listed skill."""

    model_config = ConfigDict(extra="forbid")

    entries: list[SweepEntry] = Field(min_length=1, max_length=av.MAX_SWEEP_SKILLS)
    observed_at: datetime | None = None
    client_request_id: str | None = Field(default=None, min_length=8, max_length=56)  # "-<n>" is appended

    @field_validator("observed_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("must include a timezone offset (e.g. 2026-10-04T18:30:00Z)")
        return value


class AssessmentSkillOut(BaseModel):
    skill: str
    outcome_points: int | None
    mapping_weight_bp: int
    is_pattern_target: bool


class AssessmentOut(BaseModel):
    id: int
    kind: str
    observed_at: datetime
    observed_on: date
    mode: str
    source_key: str
    notes_used: bool
    reference_used: bool
    hints_used: int
    timed: bool
    time_limit_seconds: int | None
    time_seconds: int | None
    peer_evaluated: bool
    applied: bool
    unseen_variant: bool
    difficulty: str
    followup_points: int | None
    communication_points: int | None
    rubric: dict[str, int] | None
    familiarity: str | None
    study_minutes: int | None
    skills: list[AssessmentSkillOut]
    self_rating_before: int | None
    self_rating_after: int | None
    notes: str | None
    revision_item_key: str | None
    battery_item_key: str | None
    supersedes_id: int | None
    superseded_by_id: int | None
    is_current: bool
    created_at: datetime
