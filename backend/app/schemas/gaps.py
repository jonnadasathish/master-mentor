"""Gap read models (GAP_ENGINE §11). Derived; every number is computed by the engine."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class BlockedByOut(BaseModel):
    skill: str
    score: int | None
    min_score: int


class FocusOut(BaseModel):
    stage: str | None
    focus_skill: str | None


class GapOut(BaseModel):
    skill_key: str
    name: str
    component: str
    tier: str | None
    current_score: int | None
    effective_score: int | None
    level: int | None
    confidence: str
    target_score: int | None
    floor_score: int | None
    importance: int | None
    raw_gap: int | None
    severity: str | None
    pressure_bp: int | None
    priority: int
    status: str
    rank: int
    primary_gap_type: str | None
    gap_types: list[str]
    reason_codes: list[str]
    blocked_by: list[BlockedByOut]
    parked_reason: str | None
    recommended_focus: FocusOut
    metrics: dict[str, object]


class EvidenceRefOut(BaseModel):
    source_type: str
    source_id: int
    observed_on: date | None
    level: int | None
    outcome_points: int | None
    source_key: str | None


class GapDetail(GapOut):
    evidence: dict[str, list[EvidenceRefOut]]  # reason / gap type -> the rows that caused it


class GapReportOut(BaseModel):
    phase: str
    weeks_left: str | None
    infeasible_components: list[str]
    calibration_mode: bool | None
    gaps: list[GapOut]
