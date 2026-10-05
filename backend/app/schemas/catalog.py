"""Catalog read models (API payloads). Static catalog data only; no user state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CatalogVersions(BaseModel):
    """Every component version is the shared seed_version plus that file's content fingerprint (D-044)."""

    catalog_version: str
    skill_graph_version: str
    role_profile_version: str
    problem_catalog_version: str
    mission_template_version: str
    roadmap_version: str


class CatalogFile(BaseModel):
    role: str
    fingerprint: str


class CatalogSummary(BaseModel):
    seed_version: str
    catalog_fingerprint: str
    loaded_at: datetime
    versions: CatalogVersions
    files: list[CatalogFile]
    counts: dict[str, int]


class SkillRef(BaseModel):
    key: str
    name: str
    min_score: int | None = None
    depth: int | None = None  # for transitive prerequisite listings (1 = direct)


class SkillSummary(BaseModel):
    key: str
    name: str
    group: str
    component: str
    is_pattern: bool
    active: bool
    tier: str | None
    importance: int | None
    target_score: int | None
    floor_score: int | None
    required: bool | None
    prerequisite_count: int


class MilestoneRef(BaseModel):
    key: str
    name: str
    track: str


class SkillDetail(SkillSummary):
    evidence_kinds: list[str]
    topics: list[str]
    prerequisites: list[SkillRef]
    dependents: list[SkillRef]
    milestone: MilestoneRef | None
    problem_count: int


class PrerequisiteListing(BaseModel):
    skill: str
    transitive: bool
    prerequisites: list[SkillRef]


class GroupNode(BaseModel):
    key: str
    name: str
    component: str
    skills: list[str]


class ComponentNode(BaseModel):
    component: str
    groups: list[GroupNode]


class SkillTarget(BaseModel):
    skill: str
    component: str
    tier: str
    importance: int
    target_score: int
    floor_score: int
    required: bool


class RoleProfileOut(BaseModel):
    profile_key: str
    name: str
    seniority: str
    config: dict[str, Any]
    tier_counts: dict[str, int]
    required_skill_count: int
    critical_skills: list[str]


class MilestoneOut(BaseModel):
    key: str
    name: str
    position: int
    skills: list[str]
    extra_exit: list[str]
    content: str | None
    starts_when: str | None


class TrackOut(BaseModel):
    track: str
    milestones: list[MilestoneOut]


class BaselineItemOut(BaseModel):
    key: str
    position: int
    name: str
    minutes: int
    observation_kind: str
    covers: list[str]


class RoadmapOut(BaseModel):
    tracks: list[TrackOut]
    baseline_items: list[BaselineItemOut]
    baseline_total_minutes: int


class ProblemSkillOut(BaseModel):
    skill: str
    mapping_weight_bp: int
    primary: bool


class ProblemOut(BaseModel):
    id: int
    platform: str
    platform_key: str
    title: str
    difficulty: str
    expected_minutes: int | None
    is_canonical: bool
    skills: list[ProblemSkillOut]


class TemplateOut(BaseModel):
    key: str
    component: str
    stages: list[str]
    gap_types: list[str] | None
    applies_to: list[str] | None
    item_type: str | None
    minutes: int | None
    minutes_rule: str | None
    min_budget: int | None
    difficulty: str | None
    needs_problem: bool
    observation: dict[str, Any]
    pass_rule: str
    partial_rule: str | None
    output_level: int
    next_on_pass: str | None
    next_on_fail: str | None


class TemplateResolutionOut(BaseModel):
    component: str
    stage: str
    skill: str
    gap_type: str | None
    level: int  # 1 most specific .. 5 generic fallback (MISSION_LIBRARY.md §1)
    template: TemplateOut
