"""Starting profile: self-reported context + first-run flag (single row; configuration, never evidence).

Revision ID: 0011_starting_profile
Revises: 0010_weekly_reviews
Create Date: 2026-10-05 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0011_starting_profile"
down_revision: str | None = "0010_weekly_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "starting_profile",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("onboarding_completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("experience_years", sa.SmallInteger(), nullable=True),
        sa.Column("current_role", sa.String(length=100), nullable=True),
        sa.Column("previous_role", sa.String(length=100), nullable=True),
        sa.Column("technologies_json", sa.JSON(), nullable=False),
        sa.Column("company_profile", sa.String(length=120), nullable=True),
        sa.Column("self_report_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_starting_profile")),
        sa.CheckConstraint("id = 1", name=op.f("ck_starting_profile_single_row")),
        **TABLE_OPTIONS,
    )
    # Bootstrap the single row. An install that already has a goal has effectively been through setup:
    # it is marked complete so the first-run flow is not forced on an existing preparation.
    op.execute(
        sa.text(
            "INSERT INTO starting_profile "
            "(id, onboarding_completed_at, technologies_json, self_report_json, updated_at) "
            "SELECT 1, IF(EXISTS (SELECT 1 FROM goals), UTC_TIMESTAMP(6), NULL), JSON_ARRAY(), "
            "JSON_OBJECT('strengths', JSON_ARRAY(), 'weaknesses', JSON_ARRAY(), "
            "'never_studied', JSON_ARRAY(), 'recently_studied', JSON_ARRAY()), UTC_TIMESTAMP(6)"
        )
    )


def downgrade() -> None:
    op.drop_table("starting_profile")
