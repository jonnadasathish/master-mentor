"""Problem and attempt payloads. Raw observations only: nothing here is a score."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.activity import vocabulary as av

Outcome = Literal["PASS", "PARTIAL", "FAIL"]
AttemptMode = Literal["PRACTICE", "DIAGNOSTIC", "BASELINE", "REVISION", "SIMULATION"]
MistakeCode = Literal[
    "WRONG_PATTERN",
    "NO_APPROACH",
    "MISREAD_PROBLEM",
    "EDGE_CASE_MISSED",
    "OFF_BY_ONE",
    "IMPLEMENTATION_BUG",
    "LANGUAGE_SYNTAX",
    "DATA_STRUCTURE_API",
    "WRONG_COMPLEXITY",
    "TIME_OVERRUN",
]
Difficulty = Literal["EASY", "MEDIUM", "HARD"]
Platform = Literal["LEETCODE", "OTHER"]
Score10 = Field(default=None, ge=av.SCORE_10_MIN, le=av.SCORE_10_MAX)
Rating = Field(default=None, ge=av.SELF_RATING_MIN, le=av.SELF_RATING_MAX)


class ExecutionRubric(BaseModel):
    """Optional 0-10 self-scores for interview execution (EVIDENCE_MODEL §5.2)."""

    model_config = ConfigDict(extra="forbid")

    clarification: int | None = Score10
    think_aloud: int | None = Score10
    testing: int | None = Score10
    time_management: int | None = Score10
    optimization: int | None = Score10


class ProblemAttemptInput(BaseModel):
    """What the user observed. Field names are the Spec v2 names; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    problem_id: int = Field(gt=0)
    attempted_at: datetime | None = None  # UTC-aware instant; defaults to "now" on the server
    mode: AttemptMode = "PRACTICE"
    outcome: Outcome
    seen_elsewhere: bool = False
    hints_used: int = Field(default=0, ge=0, le=av.MAX_HINTS)
    solution_viewed: bool = False
    pattern_identified: bool | None = None
    timed: bool = False
    time_limit_seconds: int | None = Field(default=None, ge=av.MIN_TIME_LIMIT_SECONDS, le=av.MAX_SECONDS)
    time_seconds: int | None = Field(default=None, ge=0, le=av.MAX_SECONDS)
    explanation_score: int | None = Score10
    complexity_correct: bool | None = None
    followup_solved: bool | None = None
    execution_rubric: ExecutionRubric | None = None
    mistakes: list[MistakeCode] = Field(default_factory=list, max_length=av.MAX_MISTAKES)
    self_rating_before: int | None = Rating
    self_rating_after: int | None = Rating
    notes: str | None = Field(default=None, max_length=av.MAX_NOTES_CHARS)
    revision_item_key: str | None = Field(default=None, max_length=96)
    battery_item_key: str | None = Field(default=None, max_length=16)
    client_request_id: str | None = Field(default=None, min_length=8, max_length=64)

    @field_validator("attempted_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("must include a timezone offset (e.g. 2026-10-04T18:30:00Z)")
        return value


class ProblemRef(BaseModel):
    id: int
    key: str  # "<PLATFORM>:<platform_key>"
    title: str
    difficulty: str
    source: Literal["CATALOG", "PERSONAL"]


class ProblemAttemptOut(BaseModel):
    id: int
    problem: ProblemRef
    attempted_at: datetime
    attempted_on: date
    mode: str
    outcome: str
    seen_elsewhere: bool
    hints_used: int
    solution_viewed: bool
    pattern_identified: bool | None
    timed: bool
    time_limit_seconds: int | None
    time_seconds: int | None
    explanation_score: int | None
    complexity_correct: bool | None
    followup_solved: bool | None
    execution_rubric: dict[str, int] | None
    mistakes: list[str]
    self_rating_before: int | None
    self_rating_after: int | None
    notes: str | None
    revision_item_key: str | None = None
    battery_item_key: str | None = None
    supersedes_id: int | None
    superseded_by_id: int | None
    is_current: bool
    created_at: datetime
    skill_mapping_bp: int | None = None  # present only when listing by skill


class ProblemSkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str
    mapping_weight_bp: Literal[5000, 10000]


class PersonalProblemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Platform = "OTHER"
    platform_key: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=2, max_length=200)
    url: str | None = Field(default=None, max_length=500, pattern=r"^https?://")
    difficulty: Difficulty
    expected_minutes: int | None = Field(default=None, ge=1, le=180)
    skills: list[ProblemSkillInput] = Field(min_length=1, max_length=6)


class LastAttempt(BaseModel):
    id: int
    attempted_at: datetime
    outcome: str


class ProblemOut(BaseModel):
    id: int
    key: str
    platform: str
    platform_key: str
    title: str
    url: str | None
    difficulty: str
    expected_minutes: int | None
    is_canonical: bool
    source: Literal["CATALOG", "PERSONAL"]
    skills: list[dict[str, object]]
    attempt_count: int
    last_attempt: LastAttempt | None
