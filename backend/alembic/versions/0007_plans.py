"""Slice 7 mentor: frozen daily_plans and plan_items (decision history, DATA_MODEL §5).

Revision ID: 0007_plans
Revises: 0006_revision
Create Date: 2026-10-04 19:02:52.212980
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0007_plans"
down_revision: str | None = "0006_revision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "daily_plans",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("goal_id", sa.BigInteger(), nullable=True),
        sa.Column("budget_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("allocated_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("calibration_mode", sa.Boolean(), nullable=False),
        sa.Column("message_rule", sa.String(length=32), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("message_payload_json", sa.JSON(), nullable=False),
        sa.Column("stop_list_json", sa.JSON(), nullable=False),
        sa.Column("dropped_json", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("regenerated_count", sa.SmallInteger(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
        sa.Column("generated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], name=op.f("fk_daily_plans_goal_id_goals")),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_daily_plans_run_id_mentor_runs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_plans")),
        sa.UniqueConstraint("plan_date", name=op.f("uq_daily_plans_plan_date")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_daily_plans_run_id"), "daily_plans", ["run_id"], unique=False)
    op.create_table(
        "plan_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column(
            "candidate_type",
            sa.Enum(
                "BASELINE",
                "GAP",
                "DIAGNOSTIC",
                "REVISION",
                "MAINTENANCE",
                "MOCK",
                "FINAL_SIMULATION",
                "FOLLOW_UP",
                name="candidate_type",
            ),
            nullable=False,
        ),
        sa.Column("candidate_key", sa.String(length=128), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("template_key", sa.String(length=64), nullable=True),
        sa.Column("stage", sa.String(length=16), nullable=True),
        sa.Column("round_type", sa.String(length=24), nullable=True),
        sa.Column("problem_ids_json", sa.JSON(), nullable=False),
        sa.Column("revision_item_key", sa.String(length=96), nullable=True),
        sa.Column("battery_item_key", sa.String(length=16), nullable=True),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("candidate_score", sa.SmallInteger(), nullable=False),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False),
        sa.Column("explanation_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "DONE", "SKIPPED", "DEFERRED", "DISCARDED", name="plan_item_status"),
            nullable=False,
        ),
        sa.Column(
            "skip_reason",
            sa.Enum("NO_TIME", "TOO_HARD", "NOT_RELEVANT", "OTHER", name="skip_reason"),
            nullable=True,
        ),
        sa.Column(
            "observation_type",
            sa.Enum("ATTEMPT", "ASSESSMENT", "MOCK", name="observation_type"),
            nullable=True,
        ),
        sa.Column("observation_id", sa.BigInteger(), nullable=True),
        sa.Column("no_evidence", sa.Boolean(), nullable=False),
        sa.Column("carried_over_from_id", sa.BigInteger(), nullable=True),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("status_changed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["carried_over_from_id"],
            ["plan_items.id"],
            name=op.f("fk_plan_items_carried_over_from_id_plan_items"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["daily_plans.id"], name=op.f("fk_plan_items_plan_id_daily_plans")
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_plan_items_skill_id_skills")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_items")),
        sa.UniqueConstraint("plan_id", "position", name=op.f("uq_plan_items_plan_id_position")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_plan_items_skill_id_status", "plan_items", ["skill_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_table("plan_items")
    op.drop_table("daily_plans")
