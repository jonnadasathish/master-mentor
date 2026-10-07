"""Speaking practice: transcript and derived metrics of a communication observation (D-087).

Purely additive: one new table that points at ``assessments``; no existing table or row is touched. Stores
transcript text and counts only; there is no audio column by design.

Revision ID: 0013_speaking_practice
Revises: 0012_learning
Create Date: 2026-10-07 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0013_speaking_practice"
down_revision: str | None = "0012_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "speaking_practices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Enum("BROWSER", "MANUAL", name="speaking_source"), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("filler_count", sa.SmallInteger(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("metrics_version", sa.String(length=16), nullable=False),
        sa.Column("self_reflection", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "(source = 'BROWSER' AND transcript IS NOT NULL) OR (source = 'MANUAL' AND transcript IS NULL)",
            name="transcript_matches_source",
        ),
        sa.CheckConstraint("duration_seconds >= 0", name="duration_non_negative"),
        sa.CheckConstraint("word_count >= 0 AND filler_count >= 0", name="counts_non_negative"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id"),
        **TABLE_OPTIONS,
    )


def downgrade() -> None:
    op.drop_table("speaking_practices")
