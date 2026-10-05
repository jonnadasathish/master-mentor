"""Slice 11: weekly_reviews (generated once per completed week; reflection editable, audited).

Revision ID: 0010_weekly_reviews
Revises: 0009_mocks_content
Create Date: 2026-10-05 04:34:46.665868
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0010_weekly_reviews"
down_revision: str | None = "0009_mocks_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("next_focus_json", sa.JSON(), nullable=False),
        sa.Column("reflection_json", sa.JSON(), nullable=True),
        sa.Column("generated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("reflected_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_weekly_reviews_run_id_mentor_runs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_reviews")),
        sa.UniqueConstraint("week_start", name=op.f("uq_weekly_reviews_week_start")),
        **TABLE_OPTIONS,
    )


def downgrade() -> None:
    op.drop_table("weekly_reviews")
