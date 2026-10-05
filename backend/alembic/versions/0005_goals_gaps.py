"""Slice 5 gap engine: versioned goals, gap_states (derived), mentor_runs.weeks_left / infeasible
components and the mentor_runs.goal_id foreign key (D-042).

Revision ID: 0005_goals_gaps
Revises: 0004_evidence
Create Date: 2026-10-04 18:14:04.479529
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0005_goals_gaps"
down_revision: str | None = "0004_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role_profile_id", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("weekday_budgets_json", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name=op.f("ck_goals_valid_range")),
        sa.ForeignKeyConstraint(
            ["role_profile_id"], ["role_profiles.id"], name=op.f("fk_goals_role_profile_id_role_profiles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_goals_role_profile_id"), "goals", ["role_profile_id"], unique=False)
    op.create_index("ix_goals_valid_from", "goals", ["valid_from"], unique=False)
    op.create_table(
        "gap_states",
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("goal_id", sa.BigInteger(), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("raw_gap", sa.SmallInteger(), nullable=True),
        sa.Column("severity", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("pressure_bp", sa.Integer(), nullable=True),
        sa.Column("primary_gap_type", sa.String(length=24), nullable=True),
        sa.Column("gap_types_json", sa.JSON(), nullable=False),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False),
        sa.Column("blocked_by_json", sa.JSON(), nullable=False),
        sa.Column("parked_reason", sa.String(length=16), nullable=True),
        sa.Column("focus_stage", sa.String(length=16), nullable=True),
        sa.Column("focus_skill", sa.String(length=64), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], name=op.f("fk_gap_states_goal_id_goals")),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_gap_states_run_id_mentor_runs")
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_gap_states_skill_id_skills")),
        sa.PrimaryKeyConstraint("skill_id", name=op.f("pk_gap_states")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_gap_states_run_id"), "gap_states", ["run_id"], unique=False)
    op.add_column("mentor_runs", sa.Column("weeks_left", sa.Numeric(precision=7, scale=2), nullable=True))
    op.add_column("mentor_runs", sa.Column("infeasible_components_json", sa.JSON(), nullable=True))
    op.create_foreign_key(op.f("fk_mentor_runs_goal_id_goals"), "mentor_runs", "goals", ["goal_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(op.f("fk_mentor_runs_goal_id_goals"), "mentor_runs", type_="foreignkey")
    op.drop_index("fk_mentor_runs_goal_id_goals", table_name="mentor_runs")  # implicit FK index (MySQL)
    op.drop_column("mentor_runs", "infeasible_components_json")
    op.drop_column("mentor_runs", "weeks_left")
    op.drop_table("gap_states")
    op.drop_table("goals")
