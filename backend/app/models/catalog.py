"""Catalog tables (DATA_MODEL.md §2): a materialized copy of seed/*.yaml, written only by the seed loader.

Natural keys (skill_key, group_key, problem (platform, platform_key), template_key, milestone_key, item_key)
identify rows across reloads; surrogate ids are preserved by upserting on natural keys. ``position`` columns
store seed-file order so listings never depend on accidental row order.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.catalog import vocabulary as v
from app.models.base import Base

COMPONENT = Enum(*v.COMPONENTS, name="component")
TEMPLATE_COMPONENT = Enum(*v.TEMPLATE_COMPONENTS, name="template_component")
TIER = Enum(*v.TIERS, name="tier")
DIFFICULTY = Enum(*v.DIFFICULTIES, name="difficulty")
PLATFORM = Enum(*v.PLATFORMS, name="platform")
SEED_VERSION = String(32)


class SkillGroup(Base):
    __tablename__ = "skill_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    component: Mapped[str] = mapped_column(COMPONENT, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (Index("ix_skills_component", "component"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("skill_groups.id"), nullable=False, index=True)
    component: Mapped[str] = mapped_column(COMPONENT, nullable=False)
    is_pattern: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_kinds: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class SkillPrerequisite(Base):
    """The only skill relationship in Spec v2: "skill requires prereq at min_score" (D-012/D-025)."""

    __tablename__ = "skill_prerequisites"
    __table_args__ = (
        CheckConstraint("min_score IN (30, 45, 60)", name="min_score_allowed"),
        CheckConstraint("skill_id <> prereq_skill_id", name="not_self"),
    )

    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    prereq_skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    min_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class RoleProfile(Base):
    __tablename__ = "role_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    seniority: Mapped[str] = mapped_column(String(32), nullable=False)
    config_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class RoleSkillTarget(Base):
    __tablename__ = "role_skill_targets"

    profile_id: Mapped[int] = mapped_column(ForeignKey("role_profiles.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    tier: Mapped[str] = mapped_column(TIER, nullable=False)
    importance: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    floor_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("platform", "platform_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # seed ids are explicit
    platform: Mapped[str] = mapped_column(PLATFORM, nullable=False)
    platform_key: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    difficulty: Mapped[str] = mapped_column(DIFFICULTY, nullable=False)
    expected_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class ProblemSkill(Base):
    __tablename__ = "problem_skills"
    __table_args__ = (CheckConstraint("mapping_weight_bp IN (5000, 10000)", name="weight_allowed"),)

    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)
    mapping_weight_bp: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class MissionTemplate(Base):
    __tablename__ = "mission_templates"
    __table_args__ = (Index("ix_mission_templates_component", "component"),)

    template_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    component: Mapped[str] = mapped_column(TEMPLATE_COMPONENT, nullable=False)
    stages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    gap_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    applies_to: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    item_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    minutes_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    min_budget: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(DIFFICULTY, nullable=True)
    needs_problem: Mapped[bool] = mapped_column(Boolean, nullable=False)
    observation_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    pass_rule: Mapped[str] = mapped_column(String(255), nullable=False)
    partial_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    next_on_pass: Mapped[str | None] = mapped_column(String(32), nullable=True)
    next_on_fail: Mapped[str | None] = mapped_column(String(32), nullable=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class RoadmapMilestone(Base):
    __tablename__ = "roadmap_milestones"
    __table_args__ = (Index("ix_roadmap_milestones_track_position", "track", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    milestone_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    track: Mapped[str] = mapped_column(String(32), nullable=False)
    track_position: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # track order in roadmap.yaml
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # order within the track
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    extra_exit_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_when: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class RoadmapMilestoneSkill(Base):
    __tablename__ = "roadmap_milestone_skills"

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"), primary_key=True
    )  # one milestone per skill
    milestone_id: Mapped[int] = mapped_column(ForeignKey("roadmap_milestones.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class BaselineItem(Base):
    __tablename__ = "baseline_items"

    item_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    observation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    covers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)


class CatalogLoad(Base):
    """One row per seed load that changed the catalog: answers "which catalog is loaded?" (D-044)."""

    __tablename__ = "catalog_loads"
    __table_args__ = (Index("ix_catalog_loads_loaded_at", "loaded_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    seed_version: Mapped[str] = mapped_column(SEED_VERSION, nullable=False)
    catalog_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    file_fingerprints_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    counts_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
