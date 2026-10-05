"""Slice 1 baseline tables (DATA_MODEL.md §3, §5, §7): app_settings, audit_log, mentor_runs.

No user_id columns (single user, D-018). Instants are UTC DATETIME(6); calendar facts are local DATEs.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

UTC_DATETIME = DATETIME(fsp=6)


class MentorRunTrigger(StrEnum):
    OBSERVATION = "OBSERVATION"
    PLAN = "PLAN"
    REBUILD = "REBUILD"
    CORRECTION = "CORRECTION"
    GOAL = "GOAL"


class PrepPhase(StrEnum):
    BUILD = "BUILD"
    CONSOLIDATE = "CONSOLIDATE"
    SHARPEN = "SHARPEN"


class AppSettings(Base):
    """Single row (id = 1). ``timezone`` is the authoritative IANA zone for all local dates."""

    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class AuditLog(Base):
    """Append-only record of every state-changing user action (DATA_MODEL.md §7)."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_log_at", "at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(96), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class MentorRun(Base):
    """One deterministic recalculation (DATA_MODEL.md §5, GLOSSARY "Mentor Run").

    ``goal_id`` references the goal version valid on ``as_of_date`` (FK since Slice 5). ``phase``,
    ``weeks_left`` and ``calibration_mode`` are NULL only for runs without an active goal.
    """

    __tablename__ = "mentor_runs"
    __table_args__ = (Index("ix_mentor_runs_as_of_date_id", "as_of_date", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger: Mapped[MentorRunTrigger] = mapped_column(
        Enum(MentorRunTrigger, name="mentor_run_trigger", native_enum=True, validate_strings=True),
        nullable=False,
    )
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    ruleset_version: Mapped[str] = mapped_column(String(16), nullable=False)
    seed_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    calibration_mode: Mapped[bool | None] = mapped_column(nullable=True)
    phase: Mapped[PrepPhase | None] = mapped_column(
        Enum(PrepPhase, name="prep_phase", native_enum=True, validate_strings=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weeks_left: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    infeasible_components_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
