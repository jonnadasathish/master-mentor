"""Learning layer: curriculum + content catalog, learning sessions, problem guides (D-083).

Catalog tables are written only by the seed loader; learning_sessions / learning_session_steps are user state.
Purely additive: no existing row is touched (problems.guide_json starts NULL until the next seed load).

Revision ID: 0012_learning
Revises: 0011_starting_profile
Create Date: 2026-10-05 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0012_learning"
down_revision: str | None = "0011_starting_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "learning_content",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_key", sa.String(length=80), nullable=False),
        sa.Column(
            "content_type",
            sa.Enum(
                "lesson",
                "concept",
                "worked_example",
                "visual_explanation",
                "concept_check",
                "quiz",
                "coding_exercise",
                "guided_problem",
                "timed_problem",
                "debugging_exercise",
                "sql_exercise",
                "design_exercise",
                "architecture_case",
                "project",
                "interview_question",
                "behavioral_question",
                "revision_card",
                name="content_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("difficulty", sa.String(length=8), nullable=True),
        sa.Column("stages_json", sa.JSON(), nullable=False),
        sa.Column("observation_kind", sa.String(length=24), nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=True),
        sa.Column("problem_ids_json", sa.JSON(), nullable=False),
        sa.Column("body_json", sa.JSON(), nullable=False),
        sa.Column("source_file", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_content")),
        sa.UniqueConstraint("content_key", name=op.f("uq_learning_content_content_key")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_learning_content_type", "learning_content", ["content_type"], unique=False)
    op.create_table(
        "learning_tracks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_key", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_tracks")),
        sa.UniqueConstraint("track_key", name=op.f("uq_learning_tracks_track_key")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "learning_topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_key", sa.String(length=80), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["track_id"], ["learning_tracks.id"], name=op.f("fk_learning_topics_track_id_learning_tracks")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_topics")),
        sa.UniqueConstraint("topic_key", name=op.f("uq_learning_topics_topic_key")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_learning_topics_track_id"), "learning_topics", ["track_id"], unique=False)
    op.create_table(
        "learning_content_skills",
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["learning_content.id"],
            name=op.f("fk_learning_content_skills_content_id_learning_content"),
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_learning_content_skills_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("content_id", "skill_id", name=op.f("pk_learning_content_skills")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_learning_content_skills_skill_id"), "learning_content_skills", ["skill_id"], unique=False
    )
    op.create_table(
        "learning_topic_skills",
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_learning_topic_skills_skill_id_skills")
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["learning_topics.id"],
            name=op.f("fk_learning_topic_skills_topic_id_learning_topics"),
        ),
        sa.PrimaryKeyConstraint("topic_id", "skill_id", name=op.f("pk_learning_topic_skills")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_learning_topic_skills_skill_id"), "learning_topic_skills", ["skill_id"], unique=False
    )
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum(
                "DIAGNOSE",
                "LEARN",
                "RECALL",
                "GUIDED",
                "INDEPENDENT",
                "TIMED",
                "EXPLAIN",
                "TRANSFER",
                "SIMULATE",
                "PATTERN_DRILL",
                "THINK_ALOUD",
                "REINFORCE",
                "REVISION",
                name="session_stage",
            ),
            nullable=False,
        ),
        sa.Column(
            "status", sa.Enum("ACTIVE", "COMPLETED", "ABANDONED", name="session_status"), nullable=False
        ),
        sa.Column("plan_item_id", sa.BigInteger(), nullable=True),
        sa.Column("budget_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("start_score", sa.SmallInteger(), nullable=True),
        sa.Column("start_level", sa.SmallInteger(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["plan_item_id"], ["plan_items.id"], name=op.f("fk_learning_sessions_plan_item_id_plan_items")
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_learning_sessions_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_sessions")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_learning_sessions_plan_item_id"), "learning_sessions", ["plan_item_id"], unique=False
    )
    op.create_index(
        "ix_learning_sessions_skill_status", "learning_sessions", ["skill_id", "status"], unique=False
    )
    op.create_table(
        "learning_session_steps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("step_kind", sa.Enum("CONTENT", "PROBLEM", "REFLECTION", name="step_kind"), nullable=False),
        sa.Column("content_key", sa.String(length=80), nullable=True),
        sa.Column("problem_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "DONE", "SKIPPED", name="step_status"), nullable=False),
        sa.Column("observation_type", sa.String(length=16), nullable=True),
        sa.Column("observation_id", sa.BigInteger(), nullable=True),
        sa.Column("points", sa.SmallInteger(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("reflection", sa.Text(), nullable=True),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["problem_id"], ["problems.id"], name=op.f("fk_learning_session_steps_problem_id_problems")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning_sessions.id"],
            name=op.f("fk_learning_session_steps_session_id_learning_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_session_steps")),
        sa.UniqueConstraint(
            "session_id", "position", name=op.f("uq_learning_session_steps_session_id_position")
        ),
        **TABLE_OPTIONS,
    )
    op.add_column("problems", sa.Column("guide_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Dropping a table drops its indexes; dropping them first fails where MySQL uses them for a foreign key.
    op.drop_column("problems", "guide_json")
    for table in (
        "learning_session_steps",
        "learning_sessions",
        "learning_topic_skills",
        "learning_content_skills",
        "learning_topics",
        "learning_tracks",
        "learning_content",
    ):
        op.drop_table(table)
