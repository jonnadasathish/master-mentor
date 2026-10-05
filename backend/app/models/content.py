"""Content tables (DATA_MODEL §3): editable with an audit event; never evidence by themselves."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.activity import vocabulary as av
from app.models.base import Base

UTC_DATETIME = DATETIME(fsp=6)


class BehavioralStory(Base):
    __tablename__ = "behavioral_stories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str | None] = mapped_column(String(255), nullable=True)
    learning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)


class StoryCompetency(Base):
    __tablename__ = "story_competencies"
    __table_args__ = (UniqueConstraint("story_id", "position"),)

    story_id: Mapped[int] = mapped_column(ForeignKey("behavioral_stories.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    architecture_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class AssessmentPrompt(Base):
    __tablename__ = "assessment_prompts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prompt_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(Enum(*av.ASSESSMENT_KINDS, name="assessment_kind"), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_key_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
