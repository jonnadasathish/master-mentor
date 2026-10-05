"""Raw activity tables (DATA_MODEL.md §4). Append-only: rows are never updated or deleted.

A correction inserts a new row whose ``supersedes_id`` points at the row it corrects (UNIQUE, so the chain is
linear). The current interpretation is the row that nothing supersedes. No derived/scored columns exist here.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.activity import vocabulary as av
from app.models.base import Base

UTC_DATETIME = DATETIME(fsp=6)


class ProblemAttempt(Base):
    __tablename__ = "problem_attempts"
    __table_args__ = (
        Index("ix_problem_attempts_problem_id_attempted_on", "problem_id", "attempted_on"),
        Index("ix_problem_attempts_attempted_on", "attempted_on"),
        Index("ix_problem_attempts_attempted_at", "attempted_at"),
        Index("ix_problem_attempts_revision_item_key", "revision_item_key"),
        CheckConstraint("hints_used >= 0", name="hints_non_negative"),
        CheckConstraint("time_seconds IS NULL OR time_seconds >= 0", name="time_non_negative"),
        CheckConstraint(
            "explanation_score IS NULL OR explanation_score BETWEEN 0 AND 10", name="explanation_range"
        ),
        CheckConstraint(
            "self_rating_before IS NULL OR self_rating_before BETWEEN 1 AND 5", name="rating_before_range"
        ),
        CheckConstraint(
            "self_rating_after IS NULL OR self_rating_after BETWEEN 1 AND 5", name="rating_after_range"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)
    attempted_on: Mapped[date] = mapped_column(Date, nullable=False)  # local date in app_settings.timezone
    attempted_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)  # UTC instant
    mode: Mapped[str] = mapped_column(Enum(*av.ATTEMPT_MODES, name="attempt_mode"), nullable=False)
    outcome: Mapped[str] = mapped_column(Enum(*av.OUTCOMES, name="outcome"), nullable=False)
    seen_elsewhere: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hints_used: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    solution_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pattern_identified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    timed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    complexity_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    followup_solved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_rubric_json: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)
    self_rating_before: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    self_rating_after: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Links to later slices (no FK until those tables exist): revision reviews, battery items, plan items.
    revision_item_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    battery_item_key: Mapped[str | None] = mapped_column(String(16), nullable=True)
    plan_item_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("problem_attempts.id"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class AttemptMistake(Base):
    __tablename__ = "attempt_mistakes"

    attempt_id: Mapped[int] = mapped_column(ForeignKey("problem_attempts.id"), primary_key=True)
    mistake_code: Mapped[str] = mapped_column(Enum(*av.MISTAKE_CODES, name="mistake_code"), primary_key=True)


class Assessment(Base):
    """Raw observation of non-problem activity (DATA_MODEL §4): quiz, explanation, design, study, ..."""

    __tablename__ = "assessments"
    __table_args__ = (
        Index("ix_assessments_observed_on", "observed_on"),
        Index("ix_assessments_kind_observed_on", "kind", "observed_on"),
        Index("ix_assessments_source_key", "source_key"),
        Index("ix_assessments_revision_item_key", "revision_item_key"),
        Index("ix_assessments_battery_item_key", "battery_item_key"),
        CheckConstraint("hints_used >= 0", name="hints_non_negative"),
        CheckConstraint("time_seconds IS NULL OR time_seconds >= 0", name="time_non_negative"),
        CheckConstraint(
            "followup_points IS NULL OR followup_points BETWEEN 0 AND 100", name="followup_range"
        ),
        CheckConstraint(
            "communication_points IS NULL OR communication_points BETWEEN 0 AND 100",
            name="communication_range",
        ),
        CheckConstraint(
            "self_rating_before IS NULL OR self_rating_before BETWEEN 1 AND 5", name="rating_before_range"
        ),
        CheckConstraint(
            "self_rating_after IS NULL OR self_rating_after BETWEEN 1 AND 5", name="rating_after_range"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Enum(*av.ASSESSMENT_KINDS, name="assessment_kind"), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    mode: Mapped[str] = mapped_column(Enum(*av.ATTEMPT_MODES, name="attempt_mode"), nullable=False)
    source_key: Mapped[str] = mapped_column(String(96), nullable=False)
    notes_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reference_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hints_used: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    timed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peer_evaluated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unseen_variant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    difficulty: Mapped[str] = mapped_column(Enum(*av.DIFFICULTIES, name="difficulty"), nullable=False)
    followup_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    communication_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rubric_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    familiarity: Mapped[str | None] = mapped_column(Enum(*av.FAMILIARITY, name="familiarity"), nullable=True)
    study_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    self_rating_before: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    self_rating_after: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_item_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    battery_item_key: Mapped[str | None] = mapped_column(String(16), nullable=True)
    plan_item_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessments.id"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class AssessmentSkill(Base):
    __tablename__ = "assessment_skills"
    __table_args__ = (
        CheckConstraint("outcome_points IS NULL OR outcome_points BETWEEN 0 AND 100", name="points_range"),
        CheckConstraint("mapping_weight_bp IN (5000, 10000)", name="weight_allowed"),
    )

    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    outcome_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    mapping_weight_bp: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_pattern_target: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RevisionItemAction(Base):
    """A recorded revision decision (DATA_MODEL §4): manual or backlog-triage suspend/resume. Replayed."""

    __tablename__ = "revision_item_actions"
    __table_args__ = (Index("ix_revision_item_actions_item_key_action_on", "item_key", "action_on"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_key: Mapped[str] = mapped_column(String(96), nullable=False)
    action: Mapped[str] = mapped_column(Enum("SUSPEND", "RESUME", name="revision_action"), nullable=False)
    reason: Mapped[str] = mapped_column(
        Enum("MANUAL", "BACKLOG_TRIAGE", name="revision_action_reason"), nullable=False
    )
    action_on: Mapped[date] = mapped_column(Date, nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("mentor_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


ROUND_TYPES = ("DSA", "CS", "LLD", "SYSTEM_DESIGN", "BEHAVIORAL", "PROJECT_DEEP_DIVE")


class Mock(Base):
    """A mock interview (or final simulation). All rounds share one local day (DATA_MODEL §4)."""

    __tablename__ = "mocks"
    __table_args__ = (Index("ix_mocks_occurred_on", "occurred_on"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
    source: Mapped[str] = mapped_column(Enum("SELF", "PEER", "PLATFORM", name="mock_source"), nullable=False)
    is_final_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_item_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("mocks.id"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class MockRoundRow(Base):
    __tablename__ = "mock_rounds"
    __table_args__ = (
        CheckConstraint("round_score BETWEEN 0 AND 100", name="score_range"),
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mock_id: Mapped[int] = mapped_column(ForeignKey("mocks.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    round_type: Mapped[str] = mapped_column(Enum(*ROUND_TYPES, name="round_type"), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    round_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    communication_points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rubric_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class MockRoundSkill(Base):
    __tablename__ = "mock_round_skills"
    __table_args__ = (CheckConstraint("outcome_points BETWEEN 0 AND 100", name="points_range"),)

    round_id: Mapped[int] = mapped_column(ForeignKey("mock_rounds.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    outcome_points: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_weakness: Mapped[bool] = mapped_column(Boolean, nullable=False)
