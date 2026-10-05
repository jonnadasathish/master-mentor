"""Profile tables (DATA_MODEL §3): versioned goals. A change inserts a new version; old rows get valid_to."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, CheckConstraint, Date, ForeignKey, Index, SmallInteger, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goals_valid_from", "valid_from"),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="valid_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_profile_id: Mapped[int] = mapped_column(ForeignKey("role_profiles.id"), nullable=False, index=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weekday_budgets_json: Mapped[list[int]] = mapped_column(JSON, nullable=False)  # Mon..Sun minutes
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)  # exclusive
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)


class StartingProfile(Base):
    """Self-reported context (single row, id = 1). Configuration, like ``app_settings``.

    It is NOT evidence and no engine reads it (EVIDENCE_MODEL: self-report never raises a skill state).
    ``onboarding_completed_at`` is the first-run flag. The goal (target role/date/hours) stays in the
    versioned ``goals`` table.
    """

    __tablename__ = "starting_profile"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    previous_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    technologies_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    company_profile: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # {strengths, weaknesses, never_studied, recently_studied}: lists of skill-group keys
    self_report_json: Mapped[dict[str, list[str]]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
