"""Profile tables (DATA_MODEL §3): versioned goals. A change inserts a new version; old rows get valid_to."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, CheckConstraint, Date, ForeignKey, Index
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
