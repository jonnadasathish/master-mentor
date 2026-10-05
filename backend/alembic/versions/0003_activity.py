"""Slice 3 activity capture: problem_attempts + attempt_mistakes (DATA_MODEL.md §4). Append-only raw facts.

Revision ID: 0003_activity
Revises: 0002_catalog
Create Date: 2026-10-04 16:20:19.939138
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0003_activity"
down_revision: str | None = "0002_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "problem_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("attempted_on", sa.Date(), nullable=False),
        sa.Column("attempted_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "mode",
            sa.Enum("PRACTICE", "DIAGNOSTIC", "BASELINE", "REVISION", "SIMULATION", name="attempt_mode"),
            nullable=False,
        ),
        sa.Column("outcome", sa.Enum("PASS", "PARTIAL", "FAIL", name="outcome"), nullable=False),
        sa.Column("seen_elsewhere", sa.Boolean(), nullable=False),
        sa.Column("hints_used", sa.SmallInteger(), nullable=False),
        sa.Column("solution_viewed", sa.Boolean(), nullable=False),
        sa.Column("pattern_identified", sa.Boolean(), nullable=True),
        sa.Column("timed", sa.Boolean(), nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=True),
        sa.Column("time_seconds", sa.Integer(), nullable=True),
        sa.Column("explanation_score", sa.SmallInteger(), nullable=True),
        sa.Column("complexity_correct", sa.Boolean(), nullable=True),
        sa.Column("followup_solved", sa.Boolean(), nullable=True),
        sa.Column("execution_rubric_json", sa.JSON(), nullable=True),
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
            "explanation_score IS NULL OR explanation_score BETWEEN 0 AND 10",
            name=op.f("ck_problem_attempts_explanation_range"),
        ),
        sa.CheckConstraint("hints_used >= 0", name=op.f("ck_problem_attempts_hints_non_negative")),
        sa.CheckConstraint(
            "self_rating_after IS NULL OR self_rating_after BETWEEN 1 AND 5",
            name=op.f("ck_problem_attempts_rating_after_range"),
        ),
        sa.CheckConstraint(
            "self_rating_before IS NULL OR self_rating_before BETWEEN 1 AND 5",
            name=op.f("ck_problem_attempts_rating_before_range"),
        ),
        sa.CheckConstraint(
            "time_seconds IS NULL OR time_seconds >= 0", name=op.f("ck_problem_attempts_time_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["problem_id"], ["problems.id"], name=op.f("fk_problem_attempts_problem_id_problems")
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["problem_attempts.id"],
            name=op.f("fk_problem_attempts_supersedes_id_problem_attempts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_attempts")),
        sa.UniqueConstraint("client_request_id", name=op.f("uq_problem_attempts_client_request_id")),
        sa.UniqueConstraint("supersedes_id", name=op.f("uq_problem_attempts_supersedes_id")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_problem_attempts_attempted_at", "problem_attempts", ["attempted_at"], unique=False)
    op.create_index("ix_problem_attempts_attempted_on", "problem_attempts", ["attempted_on"], unique=False)
    op.create_index(
        "ix_problem_attempts_problem_id_attempted_on",
        "problem_attempts",
        ["problem_id", "attempted_on"],
        unique=False,
    )
    op.create_index(
        "ix_problem_attempts_revision_item_key", "problem_attempts", ["revision_item_key"], unique=False
    )
    op.create_table(
        "attempt_mistakes",
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "mistake_code",
            sa.Enum(
                "WRONG_PATTERN",
                "NO_APPROACH",
                "MISREAD_PROBLEM",
                "EDGE_CASE_MISSED",
                "OFF_BY_ONE",
                "IMPLEMENTATION_BUG",
                "LANGUAGE_SYNTAX",
                "DATA_STRUCTURE_API",
                "WRONG_COMPLEXITY",
                "TIME_OVERRUN",
                name="mistake_code",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["problem_attempts.id"],
            name=op.f("fk_attempt_mistakes_attempt_id_problem_attempts"),
        ),
        sa.PrimaryKeyConstraint("attempt_id", "mistake_code", name=op.f("pk_attempt_mistakes")),
        **TABLE_OPTIONS,
    )


def downgrade() -> None:
    # Child first; dropping a table drops its indexes (indexes needed by FKs cannot be dropped alone).
    op.drop_table("attempt_mistakes")
    op.drop_table("problem_attempts")
