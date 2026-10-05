"""Learning layer tables (DATA_MODEL §8, LEARNING_ENGINE).

Catalog side (written only by the seed loader, natural keys): tracks, topics, topic skills, content and
content skills. User side: learning sessions and their steps. A step links to the observation it recorded
(assessment or attempt); progress is derived from observations (``source_key = content:<key>``), so nothing
here is evidence.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.catalog import vocabulary as v
from app.domain.learning import vocabulary as lv
from app.models.base import Base

UTC_DATETIME = DATETIME(fsp=6)
SEED_VERSION = String(32)


class LearningTrack(Base):
    __tablename__ = "learning_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_key: Mapped[str] = mapped_column(String(48), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    components_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class LearningTopic(Base):
    __tablename__ = "learning_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("learning_tracks.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class LearningTopicSkill(Base):
    __tablename__ = "learning_topic_skills"

    topic_id: Mapped[int] = mapped_column(ForeignKey("learning_topics.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class LearningContent(Base):
    __tablename__ = "learning_content"
    __table_args__ = (Index("ix_learning_content_type", "content_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(Enum(*lv.CONTENT_TYPES, name="content_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(8), nullable=True)
    stages_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    observation_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    problem_ids_json: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    body_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    source_file: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class LearningContentSkill(Base):
    __tablename__ = "learning_content_skills"

    content_id: Mapped[int] = mapped_column(ForeignKey("learning_content.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0 = primary skill


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (Index("ix_learning_sessions_skill_status", "skill_id", "status"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False)
    stage: Mapped[str] = mapped_column(Enum(*v.STAGES, name="session_stage"), nullable=False)
    status: Mapped[str] = mapped_column(Enum(*lv.SESSION_STATUSES, name="session_status"), nullable=False)
    plan_item_id: Mapped[int | None] = mapped_column(ForeignKey("plan_items.id"), nullable=True, index=True)
    budget_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    start_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # effective score at start
    start_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)


class LearningSessionStep(Base):
    __tablename__ = "learning_session_steps"
    __table_args__ = (UniqueConstraint("session_id", "position"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("learning_sessions.id"), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    step_kind: Mapped[str] = mapped_column(Enum(*lv.STEP_KINDS, name="step_kind"), nullable=False)
    content_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(Enum(*lv.STEP_STATUSES, name="step_status"), nullable=False)
    observation_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ASSESSMENT | ATTEMPT
    observation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
