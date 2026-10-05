"""Slice 10: mocks / mock_rounds / mock_round_skills (raw, append-only) and content tables (stories, story
competencies, projects, assessment prompts).

Revision ID: 0009_mocks_content
Revises: 0008_readiness
Create Date: 2026-10-04 19:38:24.881255
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0009_mocks_content"
down_revision: str | None = "0008_readiness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "behavioral_stories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("situation", sa.Text(), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("metric", sa.String(length=255), nullable=True),
        sa.Column("learning", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("archived_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_behavioral_stories")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "mocks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("occurred_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("source", sa.Enum("SELF", "PEER", "PLATFORM", name="mock_source"), nullable=False),
        sa.Column("is_final_simulation", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("plan_item_id", sa.BigInteger(), nullable=True),
        sa.Column("client_request_id", sa.String(length=64), nullable=True),
        sa.Column("supersedes_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["supersedes_id"], ["mocks.id"], name=op.f("fk_mocks_supersedes_id_mocks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mocks")),
        sa.UniqueConstraint("client_request_id", name=op.f("uq_mocks_client_request_id")),
        sa.UniqueConstraint("supersedes_id", name=op.f("uq_mocks_supersedes_id")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_mocks_occurred_on", "mocks", ["occurred_on"], unique=False)
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("architecture_notes", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("project_key", name=op.f("uq_projects_project_key")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "mock_rounds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mock_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column(
            "round_type",
            sa.Enum(
                "DSA", "CS", "LLD", "SYSTEM_DESIGN", "BEHAVIORAL", "PROJECT_DEEP_DIVE", name="round_type"
            ),
            nullable=False,
        ),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("round_score", sa.SmallInteger(), nullable=False),
        sa.Column("communication_points", sa.SmallInteger(), nullable=True),
        sa.Column("rubric_json", sa.JSON(), nullable=True),
        sa.CheckConstraint("duration_minutes > 0", name=op.f("ck_mock_rounds_duration_positive")),
        sa.CheckConstraint("round_score BETWEEN 0 AND 100", name=op.f("ck_mock_rounds_score_range")),
        sa.ForeignKeyConstraint(["mock_id"], ["mocks.id"], name=op.f("fk_mock_rounds_mock_id_mocks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mock_rounds")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_mock_rounds_mock_id"), "mock_rounds", ["mock_id"], unique=False)
    op.create_table(
        "assessment_prompts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("prompt_key", sa.String(length=96), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
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
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("answer_key_text", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_assessment_prompts_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_prompts")),
        sa.UniqueConstraint("prompt_key", name=op.f("uq_assessment_prompts_prompt_key")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_assessment_prompts_skill_id"), "assessment_prompts", ["skill_id"], unique=False)
    op.create_table(
        "mock_round_skills",
        sa.Column("round_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("outcome_points", sa.SmallInteger(), nullable=False),
        sa.Column("is_weakness", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "outcome_points BETWEEN 0 AND 100", name=op.f("ck_mock_round_skills_points_range")
        ),
        sa.ForeignKeyConstraint(
            ["round_id"], ["mock_rounds.id"], name=op.f("fk_mock_round_skills_round_id_mock_rounds")
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_mock_round_skills_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("round_id", "skill_id", name=op.f("pk_mock_round_skills")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_mock_round_skills_skill_id"), "mock_round_skills", ["skill_id"], unique=False)
    op.create_table(
        "story_competencies",
        sa.Column("story_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_story_competencies_skill_id_skills")
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["behavioral_stories.id"],
            name=op.f("fk_story_competencies_story_id_behavioral_stories"),
        ),
        sa.PrimaryKeyConstraint("story_id", "skill_id", name=op.f("pk_story_competencies")),
        sa.UniqueConstraint("story_id", "position", name=op.f("uq_story_competencies_story_id_position")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_story_competencies_skill_id"), "story_competencies", ["skill_id"], unique=False)


def downgrade() -> None:
    # Children before parents; dropping a table drops its indexes.
    for table in (
        "story_competencies",
        "mock_round_skills",
        "assessment_prompts",
        "mock_rounds",
        "projects",
        "mocks",
        "behavioral_stories",
    ):
        op.drop_table(table)
