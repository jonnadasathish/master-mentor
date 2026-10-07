"""Speaking practice (D-087): the transcript and derived metrics behind one communication observation.

One append-only row per ``assessments`` row recorded by a speaking exercise. The assessment stays the only
evidence; this table holds what the learner said (text only, never audio) and the deterministic metrics, so
trends such as filler rate or repeated phrases can be read across attempts. The session link is not stored
twice: ``learning_session_steps.observation_id`` already points at the assessment.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.communication import vocabulary as cv
from app.models.base import Base

UTC_DATETIME = DATETIME(fsp=6)


class SpeakingPractice(Base):
    __tablename__ = "speaking_practices"
    __table_args__ = (
        CheckConstraint(
            "(source = 'BROWSER' AND transcript IS NOT NULL) OR (source = 'MANUAL' AND transcript IS NULL)",
            name="transcript_matches_source",
        ),
        CheckConstraint("duration_seconds >= 0", name="duration_non_negative"),
        CheckConstraint("word_count >= 0 AND filler_count >= 0", name="counts_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(Enum(*cv.SPEAKING_SOURCES, name="speaking_source"), nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    filler_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    metrics_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    metrics_version: Mapped[str] = mapped_column(String(16), nullable=False)
    self_reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
