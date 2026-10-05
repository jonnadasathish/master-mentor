"""Decision tables (DATA_MODEL §5): frozen daily plans and items. Written once; status changes audited."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

UTC_DATETIME = DATETIME(fsp=6)
CANDIDATE_TYPES = (
    "BASELINE",
    "GAP",
    "DIAGNOSTIC",
    "REVISION",
    "MAINTENANCE",
    "MOCK",
    "FINAL_SIMULATION",
    "FOLLOW_UP",
)
ITEM_STATUSES = ("PENDING", "DONE", "SKIPPED", "DEFERRED", "DISCARDED")
SKIP_REASONS = ("NO_TIME", "TOO_HARD", "NOT_RELEVANT", "OTHER")


class DailyPlanRow(Base):
    __tablename__ = "daily_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("mentor_runs.id"), nullable=False, index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    budget_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    allocated_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    calibration_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message_rule: Mapped[str] = mapped_column(String(32), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    stop_list_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    dropped_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    regenerated_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class PlanItemRow(Base):
    __tablename__ = "plan_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "position"),
        Index("ix_plan_items_skill_id_status", "skill_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("daily_plans.id"), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    candidate_type: Mapped[str] = mapped_column(Enum(*CANDIDATE_TYPES, name="candidate_type"), nullable=False)
    candidate_key: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"), nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    round_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    problem_ids_json: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    revision_item_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    battery_item_key: Mapped[str | None] = mapped_column(String(16), nullable=True)
    minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    candidate_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    explanation_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(Enum(*ITEM_STATUSES, name="plan_item_status"), nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(Enum(*SKIP_REASONS, name="skip_reason"), nullable=True)
    observation_type: Mapped[str | None] = mapped_column(
        Enum("ATTEMPT", "ASSESSMENT", "MOCK", name="observation_type"), nullable=True
    )
    observation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    no_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    carried_over_from_id: Mapped[int | None] = mapped_column(ForeignKey("plan_items.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)


class WeeklyReviewRow(Base):
    """Generated once after the week ends (decision history); only the reflection is edited (audited)."""

    __tablename__ = "weekly_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("mentor_runs.id"), nullable=True)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)
    metrics_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    next_focus_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    reflection_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    reflected_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
