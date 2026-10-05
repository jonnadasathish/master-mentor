"""Slice 4 evidence engine: assessments + assessment_skills (raw, append-only, DATA_MODEL §4) and the derived,
rebuildable evidence / skill_states / skill_daily_snapshots tables (DATA_MODEL §6).

Revision ID: 0004_evidence
Revises: 0003_activity
Create Date: 2026-10-04 17:37:17.245779
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0004_evidence"
down_revision: str | None = "0003_activity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "STUDY_SESSION",
                "SELF_ASSESSMENT",
                "RECALL_QUIZ",
                "PATTERN_DRILL",
                "CONCEPT_EXPLAIN",
                "CODE_EXERCISE",
                "ESTIMATION_DRILL",
                "SD_DESIGN",
                "LLD_DESIGN",
                "MACHINE_CODING",
                "STORY_REHEARSAL",
                "PROJECT_WALKTHROUGH",
                "APPLIED_TASK",
                name="assessment_kind",
            ),
            nullable=False,
        ),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("observed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "mode",
            sa.Enum("PRACTICE", "DIAGNOSTIC", "BASELINE", "REVISION", "SIMULATION", name="attempt_mode"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(length=96), nullable=False),
        sa.Column("notes_used", sa.Boolean(), nullable=False),
        sa.Column("reference_used", sa.Boolean(), nullable=False),
        sa.Column("hints_used", sa.SmallInteger(), nullable=False),
        sa.Column("timed", sa.Boolean(), nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=True),
        sa.Column("time_seconds", sa.Integer(), nullable=True),
        sa.Column("peer_evaluated", sa.Boolean(), nullable=False),
        sa.Column("applied", sa.Boolean(), nullable=False),
        sa.Column("unseen_variant", sa.Boolean(), nullable=False),
        sa.Column("difficulty", sa.Enum("EASY", "MEDIUM", "HARD", name="difficulty"), nullable=False),
        sa.Column("followup_points", sa.SmallInteger(), nullable=True),
        sa.Column("communication_points", sa.SmallInteger(), nullable=True),
        sa.Column("rubric_json", sa.JSON(), nullable=True),
        sa.Column("familiarity", sa.Enum("NONE", "SOME", "SOLID", name="familiarity"), nullable=True),
        sa.Column("study_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("self_rating_before", sa.SmallInteger(), nullable=True),
        sa.Column("self_rating_after", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("revision_item_key", sa.String(length=96), nullable=True),
        sa.Column("battery_item_key", sa.String(length=16), nullable=True),
        sa.Column("plan_item_id", sa.BigInteger(), nullable=True),
        sa.Column("client_request_id", sa.String(length=64), nullable=True),
        sa.Column("supersedes_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "communication_points IS NULL OR communication_points BETWEEN 0 AND 100",
            name=op.f("ck_assessments_communication_range"),
        ),
        sa.CheckConstraint(
            "followup_points IS NULL OR followup_points BETWEEN 0 AND 100",
            name=op.f("ck_assessments_followup_range"),
        ),
        sa.CheckConstraint("hints_used >= 0", name=op.f("ck_assessments_hints_non_negative")),
        sa.CheckConstraint(
            "self_rating_after IS NULL OR self_rating_after BETWEEN 1 AND 5",
            name=op.f("ck_assessments_rating_after_range"),
        ),
        sa.CheckConstraint(
            "self_rating_before IS NULL OR self_rating_before BETWEEN 1 AND 5",
            name=op.f("ck_assessments_rating_before_range"),
        ),
        sa.CheckConstraint(
            "time_seconds IS NULL OR time_seconds >= 0", name=op.f("ck_assessments_time_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"], ["assessments.id"], name=op.f("fk_assessments_supersedes_id_assessments")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
        sa.UniqueConstraint("client_request_id", name=op.f("uq_assessments_client_request_id")),
        sa.UniqueConstraint("supersedes_id", name=op.f("uq_assessments_supersedes_id")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_assessments_battery_item_key", "assessments", ["battery_item_key"], unique=False)
    op.create_index("ix_assessments_kind_observed_on", "assessments", ["kind", "observed_on"], unique=False)
    op.create_index("ix_assessments_observed_on", "assessments", ["observed_on"], unique=False)
    op.create_index("ix_assessments_revision_item_key", "assessments", ["revision_item_key"], unique=False)
    op.create_index("ix_assessments_source_key", "assessments", ["source_key"], unique=False)
    op.create_table(
        "assessment_skills",
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("outcome_points", sa.SmallInteger(), nullable=True),
        sa.Column("mapping_weight_bp", sa.SmallInteger(), nullable=False),
        sa.Column("is_pattern_target", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "mapping_weight_bp IN (5000, 10000)", name=op.f("ck_assessment_skills_weight_allowed")
        ),
        sa.CheckConstraint(
            "outcome_points IS NULL OR outcome_points BETWEEN 0 AND 100",
            name=op.f("ck_assessment_skills_points_range"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["assessments.id"], name=op.f("fk_assessment_skills_assessment_id_assessments")
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_assessment_skills_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("assessment_id", "skill_id", name=op.f("pk_assessment_skills")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_assessment_skills_skill_id"), "assessment_skills", ["skill_id"], unique=False)
    op.create_table(
        "evidence",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("ATTEMPT", "ASSESSMENT", "MOCK_ROUND", name="evidence_source"),
            nullable=False,
        ),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "rule",
            sa.Enum("MAPPED", "DERIVED", "MISTAKE", "ASSESSMENT", "MOCK", name="evidence_rule"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=32), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("outcome_points", sa.SmallInteger(), nullable=True),
        sa.Column("is_scoring", sa.Boolean(), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("observed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("difficulty_bp", sa.Integer(), nullable=False),
        sa.Column("mapping_bp", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("source_key", sa.String(length=96), nullable=False),
        sa.Column("timed", sa.Boolean(), nullable=False),
        sa.Column("time_ratio_bp", sa.Integer(), nullable=True),
        sa.Column("within_limit", sa.Boolean(), nullable=True),
        sa.Column("depth_points", sa.SmallInteger(), nullable=True),
        sa.Column("communication_points", sa.SmallInteger(), nullable=True),
        sa.Column("self_rating_before", sa.SmallInteger(), nullable=True),
        sa.Column("pattern_identified", sa.Boolean(), nullable=True),
        sa.Column("is_unseen", sa.Boolean(), nullable=True),
        sa.Column("is_weakness", sa.Boolean(), nullable=False),
        sa.Column("familiarity", sa.String(length=8), nullable=True),
        sa.Column("study_minutes", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_evidence_skill_id_skills")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "skill_id",
            "ruleset_version",
            name=op.f("uq_evidence_source_type_source_id_skill_id_ruleset_version"),
        ),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_evidence_ruleset_version_skill_id_observed_on",
        "evidence",
        ["ruleset_version", "skill_id", "observed_on"],
        unique=False,
    )
    op.create_table(
        "skill_daily_snapshots",
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("effective_score", sa.SmallInteger(), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=True),
        sa.Column("confidence", sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", name="confidence"), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_skill_daily_snapshots_run_id_mentor_runs")
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_skill_daily_snapshots_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("snapshot_date", "skill_id", name=op.f("pk_skill_daily_snapshots")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_skill_daily_snapshots_skill_id"), "skill_daily_snapshots", ["skill_id"], unique=False
    )
    op.create_table(
        "skill_states",
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=True),
        sa.Column("quality", sa.Numeric(precision=9, scale=4), nullable=True),
        sa.Column("confidence", sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", name="confidence"), nullable=False),
        sa.Column("effective_score", sa.SmallInteger(), nullable=True),
        sa.Column("peak_score", sa.SmallInteger(), nullable=True),
        sa.Column("evidence_count", sa.SmallInteger(), nullable=False),
        sa.Column("distinct_sources", sa.SmallInteger(), nullable=False),
        sa.Column("last_practiced_on", sa.Date(), nullable=True),
        sa.Column("last_observed_on", sa.Date(), nullable=True),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("reality_capped", sa.Boolean(), nullable=False),
        sa.Column("declared_unknown", sa.Boolean(), nullable=False),
        sa.Column("considered_evidence_json", sa.JSON(), nullable=False),
        sa.Column("qualifying_evidence_json", sa.JSON(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_skill_states_run_id_mentor_runs")
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_skill_states_skill_id_skills")),
        sa.PrimaryKeyConstraint("skill_id", name=op.f("pk_skill_states")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_skill_states_run_id"), "skill_states", ["run_id"], unique=False)


def downgrade() -> None:
    # Derived tables first, then children before parents; dropping a table drops its indexes.
    op.drop_table("skill_states")
    op.drop_table("skill_daily_snapshots")
    op.drop_table("evidence")
    op.drop_table("assessment_skills")
    op.drop_table("assessments")
