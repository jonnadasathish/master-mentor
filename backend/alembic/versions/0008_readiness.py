"""Slice 8 readiness engine: readiness_snapshots (derived, one per local date, READINESS_MODEL §10).

Revision ID: 0008_readiness
Revises: 0007_plans
Create Date: 2026-10-04 19:17:57.498537
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_readiness"
down_revision: str | None = "0007_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "readiness_snapshots",
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "NOT_MEASURED",
                "FOUNDATION",
                "DEVELOPING",
                "INTERVIEW_READY",
                "STRONG",
                name="readiness_state",
            ),
            nullable=False,
        ),
        sa.Column("weighted_score", sa.SmallInteger(), nullable=False),
        sa.Column("limiting_component", sa.String(length=24), nullable=True),
        sa.Column("simulation_eligible", sa.Boolean(), nullable=False),
        sa.Column("lapsed", sa.Boolean(), nullable=False),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("gates_json", sa.JSON(), nullable=False),
        sa.Column("blockers_json", sa.JSON(), nullable=False),
        sa.Column("all_failing_json", sa.JSON(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["mentor_runs.id"], name=op.f("fk_readiness_snapshots_run_id_mentor_runs")
        ),
        sa.PrimaryKeyConstraint("snapshot_date", name=op.f("pk_readiness_snapshots")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_readiness_snapshots_run_id"), "readiness_snapshots", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_table("readiness_snapshots")
