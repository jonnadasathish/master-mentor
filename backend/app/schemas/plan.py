"""Today / plan read models and plan-item actions (MENTOR_ENGINE §11, API_SPEC "Today and plan")."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SkipReason = Literal["NO_TIME", "TOO_HARD", "NOT_RELEVANT", "OTHER"]


class ProblemRefOut(BaseModel):
    id: int
    key: str
    title: str
    difficulty: str
    url: str | None


class TemplateOut(BaseModel):
    key: str
    observation: dict[str, Any]
    pass_rule: str
    output_level: int
    next_on_pass: str | None


class PlanItemOut(BaseModel):
    id: int
    position: int
    candidate_type: str
    candidate_key: str
    skill: str | None
    stage: str | None
    minutes: int
    candidate_score: int
    template: TemplateOut | None
    problems: list[ProblemRefOut]
    revision_item_key: str | None
    battery_item_key: str | None
    round_type: str | None
    reason_codes: list[str]
    explanation: dict[str, Any]
    status: str
    skip_reason: str | None
    observation_type: str | None
    observation_id: int | None
    no_evidence: bool
    carried_over_from_id: int | None
    started_at: datetime | None
    completed_at: datetime | None


class MessageOut(BaseModel):
    rule: str
    text: str
    payload: dict[str, Any]


class PlanOut(BaseModel):
    id: int
    plan_date: date
    run_id: int
    ruleset_version: str
    budget_minutes: int
    allocated_minutes: int
    unallocated_minutes: int
    done_minutes: int
    phase: str
    calibration_mode: bool
    regenerated_count: int
    items: list[PlanItemOut]
    stop_list: list[dict[str, Any]]
    dropped: list[dict[str, Any]]
    message: MessageOut


class CalibrationOut(BaseModel):
    active: bool
    assessed: int
    required: int
    assessed_pct: int
    battery_done: int
    battery_total: int
    next_item: str | None


class TopGapOut(BaseModel):
    skill_key: str
    status: str
    priority: int
    primary_gap_type: str | None
    focus_stage: str | None
    reason_codes: list[str]


class ReadinessSummaryOut(BaseModel):
    state: str
    weighted_score: int
    limiting_component: str | None
    blockers: list[dict[str, Any]]


class TodayOut(BaseModel):
    plan_date: date
    phase: str
    weeks_left: str | None
    goal_exists: bool
    calibration: CalibrationOut
    readiness: ReadinessSummaryOut
    top_gaps: list[TopGapOut]
    revisions: dict[str, int]
    plan: PlanOut


class WeekTrackOut(BaseModel):
    track: str
    minutes: int
    weekly_target: int


class WeekRevisionOut(BaseModel):
    planned: int
    done: int
    completion_pct: int | None


class WeekOut(BaseModel):
    """Week-to-date context for the Today page (read-only; recorded practice, not plan minutes)."""

    plan_date: date
    week_start: date
    week_end: date
    preparation_day: int | None
    target_minutes: int | None
    practice_minutes: int
    active_days: int
    minutes_by_track: list[WeekTrackOut]
    revision: WeekRevisionOut


class ObservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["ATTEMPT", "ASSESSMENT", "MOCK"]
    body: dict[str, Any]


class CompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: ObservationIn | None = None
    no_evidence: bool = False


class SkipIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skip_reason: SkipReason


class ItemActionOut(BaseModel):
    item: PlanItemOut
    observation: dict[str, Any] | None = None


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=200)
