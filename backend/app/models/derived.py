"""Derived, rebuildable tables (DATA_MODEL §6). Written only by mentor runs; never edited by hand."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CONFIDENCE = Enum("NONE", "LOW", "MEDIUM", "HIGH", name="confidence")


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "skill_id", "ruleset_version"),
        Index(
            "ix_evidence_ruleset_version_skill_id_observed_on", "ruleset_version", "skill_id", "observed_on"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)
    source_type: Mapped[str] = mapped_column(
        Enum("ATTEMPT", "ASSESSMENT", "MOCK_ROUND", name="evidence_source")
    )
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False)
    rule: Mapped[str] = mapped_column(
        Enum("MAPPED", "DERIVED", "MISTAKE", "ASSESSMENT", "MOCK", name="evidence_rule"), nullable=False
    )
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    outcome_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_scoring: Mapped[bool] = mapped_column(Boolean, nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    difficulty_bp: Mapped[int] = mapped_column(Integer, nullable=False)
    mapping_bp: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_key: Mapped[str] = mapped_column(String(96), nullable=False)
    timed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_ratio_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    within_limit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    depth_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    communication_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    self_rating_before: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    pattern_identified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_unseen: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_weakness: Mapped[bool] = mapped_column(Boolean, nullable=False)
    familiarity: Mapped[str | None] = mapped_column(String(8), nullable=True)
    study_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class SkillState(Base):
    """Current state per skill (overwritten by every mentor run). History lives in skill_daily_snapshots."""

    __tablename__ = "skill_states"

    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("mentor_runs.id"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    quality: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    confidence: Mapped[str] = mapped_column(CONFIDENCE, nullable=False)
    effective_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    peak_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    evidence_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    distinct_sources: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    last_practiced_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    label: Mapped[str] = mapped_column(String(16), nullable=False)
    reality_capped: Mapped[bool] = mapped_column(Boolean, nullable=False)
    declared_unknown: Mapped[bool] = mapped_column(Boolean, nullable=False)
    considered_evidence_json: Mapped[list[list[object]]] = mapped_column(JSON, nullable=False)
    qualifying_evidence_json: Mapped[list[list[object]]] = mapped_column(JSON, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)


class SkillDailySnapshot(Base):
    __tablename__ = "skill_daily_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("mentor_runs.id"), nullable=False)
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    effective_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    confidence: Mapped[str] = mapped_column(CONFIDENCE, nullable=False)
    priority: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # filled from Slice 5
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # filled from Slice 5


class GapState(Base):
    """Current gap per skill (GAP_ENGINE §11), overwritten by every mentor run."""

    __tablename__ = "gap_states"

    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("mentor_runs.id"), nullable=False, index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    raw_gap: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    severity: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    pressure_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_gap_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    gap_types_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reason_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    blocked_by_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    parked_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)
    focus_stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    focus_skill: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)


class RevisionItemRow(Base):
    """Revision projection (REVISION_ENGINE §1): rebuilt by replaying observations + revision_item_actions."""

    __tablename__ = "revision_items"
    __table_args__ = (Index("ix_revision_items_state_due_date", "state", "due_date"),)

    item_key: Mapped[str] = mapped_column(String(96), primary_key=True)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(96), nullable=False)
    ladder: Mapped[str] = mapped_column(Enum("STANDARD", "MOCKW", name="revision_ladder"), nullable=False)
    state: Mapped[str] = mapped_column(
        Enum("ACTIVE", "SUSPENDED", "GRADUATED", name="revision_state"), nullable=False
    )
    suspend_reason: Mapped[str | None] = mapped_column(
        Enum("LEECH", "BACKLOG_TRIAGE", "MANUAL", name="revision_suspend_reason"), nullable=True
    )
    interval_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lapses: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    needs_reinforcement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_on: Mapped[date] = mapped_column(Date, nullable=False)
    last_reviewed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    suspended_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("mentor_runs.id"), nullable=False)


class ReadinessSnapshot(Base):
    """One per local date, from that date's last mentor run (READINESS_MODEL §10). Rebuildable."""

    __tablename__ = "readiness_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("mentor_runs.id"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        Enum("NOT_MEASURED", "FOUNDATION", "DEVELOPING", "INTERVIEW_READY", "STRONG", name="readiness_state"),
        nullable=False,
    )
    weighted_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    limiting_component: Mapped[str | None] = mapped_column(String(24), nullable=True)
    simulation_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    lapsed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    components_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    gates_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    blockers_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    all_failing_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)
