"""Slice 6 revision engine: revision_item_actions (raw, append-only decisions) and revision_items (derived
projection, REVISION_ENGINE §1).

Revision ID: 0006_revision
Revises: 0005_goals_gaps
Create Date: 2026-10-04 18:38:46.885991
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0006_revision"
down_revision: str | None = "0005_goals_gaps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "revision_item_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_key", sa.String(length=96), nullable=False),
        sa.Column("action", sa.Enum("SUSPEND", "RESUME", name="revision_action"), nullable=False),
        sa.Column(
            "reason", sa.Enum("MANUAL", "BACKLOG_TRIAGE", name="revision_action_reason"), nullable=False
        ),
        sa.Column("action_on", sa.Date(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_revision_item_actions_run_id_mentor_runs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_revision_item_actions")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_revision_item_actions_item_key_action_on",
        "revision_item_actions",
        ["item_key", "action_on"],
        unique=False,
    )
    op.create_table(
        "revision_items",
        sa.Column("item_key", sa.String(length=96), nullable=False),
        sa.Column("item_type", sa.String(length=16), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("subject_ref", sa.String(length=96), nullable=False),
        sa.Column("ladder", sa.Enum("STANDARD", "MOCKW", name="revision_ladder"), nullable=False),
        sa.Column(
            "state", sa.Enum("ACTIVE", "SUSPENDED", "GRADUATED", name="revision_state"), nullable=False
        ),
        sa.Column(
            "suspend_reason",
            sa.Enum("LEECH", "BACKLOG_TRIAGE", "MANUAL", name="revision_suspend_reason"),
            nullable=True,
        ),
        sa.Column("interval_index", sa.SmallInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("lapses", sa.SmallInteger(), nullable=False),
        sa.Column("needs_reinforcement", sa.Boolean(), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("created_on", sa.Date(), nullable=False),
        sa.Column("last_reviewed_on", sa.Date(), nullable=True),
        sa.Column("suspended_on", sa.Date(), nullable=True),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_revision_items_run_id_mentor_runs")
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_revision_items_skill_id_skills")),
        sa.PrimaryKeyConstraint("item_key", name=op.f("pk_revision_items")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_revision_items_skill_id"), "revision_items", ["skill_id"], unique=False)
    op.create_index("ix_revision_items_state_due_date", "revision_items", ["state", "due_date"], unique=False)


def downgrade() -> None:
    op.drop_table("revision_items")
    op.drop_table("revision_item_actions")
