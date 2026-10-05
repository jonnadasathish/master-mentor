"""Slice 2 catalog: materialized seed tables + catalog_loads (DATA_MODEL.md §2, D-044).

Revision ID: 0002_catalog
Revises: 0001_baseline
Create Date: 2026-10-04 15:07:00.852157
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0002_catalog"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "baseline_items",
        sa.Column("item_key", sa.String(length=16), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("observation_kind", sa.String(length=32), nullable=False),
        sa.Column("covers_json", sa.JSON(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("item_key", name=op.f("pk_baseline_items")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "catalog_loads",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.Column("catalog_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("file_fingerprints_json", sa.JSON(), nullable=False),
        sa.Column("counts_json", sa.JSON(), nullable=False),
        sa.Column("loaded_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_loads")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_catalog_loads_loaded_at", "catalog_loads", ["loaded_at"], unique=False)
    op.create_table(
        "mission_templates",
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column(
            "component",
            sa.Enum(
                "dsa",
                "coding",
                "cs",
                "lld",
                "system_design",
                "behavioral",
                "project",
                "generic",
                "revision",
                "mock",
                name="template_component",
            ),
            nullable=False,
        ),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("gap_types", sa.JSON(), nullable=True),
        sa.Column("applies_to", sa.JSON(), nullable=True),
        sa.Column("item_type", sa.String(length=32), nullable=True),
        sa.Column("minutes", sa.SmallInteger(), nullable=True),
        sa.Column("minutes_rule", sa.String(length=255), nullable=True),
        sa.Column("min_budget", sa.SmallInteger(), nullable=True),
        sa.Column("difficulty", sa.Enum("EASY", "MEDIUM", "HARD", name="difficulty"), nullable=True),
        sa.Column("needs_problem", sa.Boolean(), nullable=False),
        sa.Column("observation_json", sa.JSON(), nullable=False),
        sa.Column("pass_rule", sa.String(length=255), nullable=False),
        sa.Column("partial_rule", sa.String(length=255), nullable=True),
        sa.Column("output_level", sa.SmallInteger(), nullable=False),
        sa.Column("next_on_pass", sa.String(length=32), nullable=True),
        sa.Column("next_on_fail", sa.String(length=32), nullable=True),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("template_key", name=op.f("pk_mission_templates")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_mission_templates_component", "mission_templates", ["component"], unique=False)
    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.Enum("LEETCODE", "OTHER", name="platform"), nullable=False),
        sa.Column("platform_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("difficulty", sa.Enum("EASY", "MEDIUM", "HARD", name="difficulty"), nullable=False),
        sa.Column("expected_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problems")),
        sa.UniqueConstraint("platform", "platform_key", name=op.f("uq_problems_platform_platform_key")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "roadmap_milestones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("milestone_key", sa.String(length=32), nullable=False),
        sa.Column("track", sa.String(length=32), nullable=False),
        sa.Column("track_position", sa.SmallInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("extra_exit_json", sa.JSON(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("starts_when", sa.String(length=255), nullable=True),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roadmap_milestones")),
        sa.UniqueConstraint("milestone_key", name=op.f("uq_roadmap_milestones_milestone_key")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_roadmap_milestones_track_position", "roadmap_milestones", ["track", "position"], unique=False
    )
    op.create_table(
        "role_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("seniority", sa.String(length=32), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_profiles")),
        sa.UniqueConstraint("profile_key", name=op.f("uq_role_profiles_profile_key")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "skill_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "component",
            sa.Enum("dsa", "coding", "cs", "lld", "system_design", "behavioral", "project", name="component"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_groups")),
        sa.UniqueConstraint("group_key", name=op.f("uq_skill_groups_group_key")),
        **TABLE_OPTIONS,
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("skill_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column(
            "component",
            sa.Enum("dsa", "coding", "cs", "lld", "system_design", "behavioral", "project", name="component"),
            nullable=False,
        ),
        sa.Column("is_pattern", sa.Boolean(), nullable=False),
        sa.Column("evidence_kinds", sa.JSON(), nullable=False),
        sa.Column("topics", sa.JSON(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["skill_groups.id"], name=op.f("fk_skills_group_id_skill_groups")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("skill_key", name=op.f("uq_skills_skill_key")),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_skills_component", "skills", ["component"], unique=False)
    op.create_index(op.f("ix_skills_group_id"), "skills", ["group_id"], unique=False)
    op.create_table(
        "problem_skills",
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("mapping_weight_bp", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "mapping_weight_bp IN (5000, 10000)", name=op.f("ck_problem_skills_weight_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["problem_id"], ["problems.id"], name=op.f("fk_problem_skills_problem_id_problems")
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_problem_skills_skill_id_skills")),
        sa.PrimaryKeyConstraint("problem_id", "skill_id", name=op.f("pk_problem_skills")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_problem_skills_skill_id"), "problem_skills", ["skill_id"], unique=False)
    op.create_table(
        "roadmap_milestone_skills",
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("milestone_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["milestone_id"],
            ["roadmap_milestones.id"],
            name=op.f("fk_roadmap_milestone_skills_milestone_id_roadmap_milestones"),
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_roadmap_milestone_skills_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("skill_id", name=op.f("pk_roadmap_milestone_skills")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_roadmap_milestone_skills_milestone_id"),
        "roadmap_milestone_skills",
        ["milestone_id"],
        unique=False,
    )
    op.create_table(
        "role_skill_targets",
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.Enum("T1", "T2", "T3", "T4", name="tier"), nullable=False),
        sa.Column("importance", sa.SmallInteger(), nullable=False),
        sa.Column("target_score", sa.SmallInteger(), nullable=False),
        sa.Column("floor_score", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["role_profiles.id"], name=op.f("fk_role_skill_targets_profile_id_role_profiles")
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_role_skill_targets_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("profile_id", "skill_id", name=op.f("pk_role_skill_targets")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_role_skill_targets_skill_id"), "role_skill_targets", ["skill_id"], unique=False)
    op.create_table(
        "skill_prerequisites",
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("prereq_skill_id", sa.Integer(), nullable=False),
        sa.Column("min_score", sa.SmallInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "min_score IN (30, 45, 60)", name=op.f("ck_skill_prerequisites_min_score_allowed")
        ),
        sa.CheckConstraint("skill_id <> prereq_skill_id", name=op.f("ck_skill_prerequisites_not_self")),
        sa.ForeignKeyConstraint(
            ["prereq_skill_id"], ["skills.id"], name=op.f("fk_skill_prerequisites_prereq_skill_id_skills")
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_skill_prerequisites_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("skill_id", "prereq_skill_id", name=op.f("pk_skill_prerequisites")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_skill_prerequisites_prereq_skill_id"),
        "skill_prerequisites",
        ["prereq_skill_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop child tables first; dropping a table also drops its indexes (MySQL refuses to drop an index
    # that a foreign key still needs, so indexes are never dropped separately here).
    for table in (
        "roadmap_milestone_skills",
        "roadmap_milestones",
        "baseline_items",
        "problem_skills",
        "problems",
        "mission_templates",
        "role_skill_targets",
        "role_profiles",
        "skill_prerequisites",
        "skills",
        "skill_groups",
        "catalog_loads",
    ):
        op.drop_table(table)
