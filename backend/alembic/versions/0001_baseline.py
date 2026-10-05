"""Slice 1 baseline: app_settings, audit_log, mentor_runs (DATA_MODEL.md §3, §5, §7).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

from app.config import get_settings

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}
UTC_DATETIME = mysql.DATETIME(fsp=6)


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_app_settings"),
        sa.CheckConstraint("id = 1", name="ck_app_settings_single_row"),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("at", UTC_DATETIME, nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(96), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_audit_log_entity_type_entity_id", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_at", "audit_log", ["at"])

    op.create_table(
        "mentor_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_at", UTC_DATETIME, nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum("OBSERVATION", "PLAN", "REBUILD", "CORRECTION", "GOAL", name="mentor_run_trigger"),
            nullable=False,
        ),
        sa.Column("goal_id", sa.BigInteger(), nullable=True),  # FK added with the goals table (Slice 4)
        sa.Column("ruleset_version", sa.String(16), nullable=False),
        sa.Column("seed_version", sa.String(32), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("calibration_mode", sa.Boolean(), nullable=True),
        sa.Column("phase", sa.Enum("BUILD", "CONSOLIDATE", "SHARPEN", name="prep_phase"), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_mentor_runs"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_mentor_runs_as_of_date_id", "mentor_runs", ["as_of_date", "id"])

    # Bootstrap the single settings row. The configured default timezone is used ONLY here;
    # afterwards app_settings.timezone is authoritative (DECISION_LOG D-039).
    op.execute(
        sa.text(
            "INSERT INTO app_settings (id, timezone, display_name, created_at) "
            "VALUES (1, :tz, 'Owner', UTC_TIMESTAMP(6))"
        ).bindparams(tz=get_settings().app_default_timezone)
    )


def downgrade() -> None:
    op.drop_index("ix_mentor_runs_as_of_date_id", table_name="mentor_runs")
    op.drop_table("mentor_runs")
    op.drop_index("ix_audit_log_at", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_type_entity_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("app_settings")
