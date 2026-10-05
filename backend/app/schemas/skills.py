"""Skill state read models (derived data; every response carries meta.run_id + ruleset_version)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class SkillStateOut(BaseModel):
    score: int | None
    effective_score: int | None
    level: int | None
    confidence: str
    label: str
    peak_score: int | None
    evidence_count: int
    distinct_sources: int
    last_practiced_on: date | None
    last_observed_on: date | None
    reality_capped: bool
    declared_unknown: bool
    assessed: bool


class GapSummary(BaseModel):
    status: str
    priority: int
    rank: int
    primary_gap_type: str | None
    focus_stage: str | None
    focus_skill: str | None
    reason_codes: list[str]
    blocked_by: list[dict[str, object]]
    parked_reason: str | None


class SkillWithState(BaseModel):
    key: str
    name: str
    group: str
    component: str
    tier: str | None
    importance: int | None
    target_score: int | None
    floor_score: int | None
    required: bool | None
    state: SkillStateOut
    gap: GapSummary | None = None


class EvidenceOut(BaseModel):
    source_type: str
    source_id: int
    rule: str
    kind: str | None
    level: int
    outcome_points: int | None
    is_scoring: bool
    observed_on: date
    observed_at: datetime
    difficulty_bp: int
    mapping_bp: int
    source_key: str
    timed: bool
    within_limit: bool | None
    is_unseen: bool | None
    is_weakness: bool
    familiarity: str | None
    considered: bool  # used in the quality average
    qualifying: bool  # counted for the level


class PrerequisiteStatus(BaseModel):
    skill: str
    min_score: int
    effective_score: int | None
    satisfied: bool


class FocusPreview(BaseModel):
    stage: str
    template_key: str | None
    minutes: int | None
    pass_rule: str | None
    observation_kind: str | None


class SkillDetail(SkillWithState):
    prerequisites: list[PrerequisiteStatus]
    dependents: list[str]
    milestone: dict[str, str] | None
    revision_items: list[dict[str, object]]
    focus: FocusPreview | None
    evidence: list[EvidenceOut]  # newest first, at most 50


class BatteryItemOut(BaseModel):
    key: str
    position: int
    name: str
    minutes: int
    observation_kind: str
    covers: list[str]
    complete: bool


class BaselineOut(BaseModel):
    items: list[BatteryItemOut]
    battery_complete: bool
    battery_done: int
    battery_total: int
    next_item: str | None
    required: int
    assessed_required: int
    assessed_pct: int
    calibration_mode: bool
    # D-080: user-facing status and effort. phase is NOT_STARTED / IN_PROGRESS / ENOUGH_MEASURED / COMPLETE.
    phase: str
    personalization_threshold_pct: int
    minutes_total: int
    minutes_done: int
    minutes_remaining: int
    typical_daily_minutes: int | None
    estimated_days: int | None
