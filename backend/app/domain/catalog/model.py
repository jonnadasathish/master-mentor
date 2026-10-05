"""Validated, typed catalog (the output of ``validate_seed``). Immutable; order follows the seed files."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.domain.learning.model import LearningCatalog


@dataclass(frozen=True)
class SkillGroup:
    key: str
    name: str
    component: str


@dataclass(frozen=True)
class Prerequisite:
    skill: str
    min_score: int


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    parent: str  # skill group key
    component: str
    is_pattern: bool
    prerequisites: tuple[Prerequisite, ...]
    evidence_kinds: tuple[str, ...]
    topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class TierSpec:
    tier: str
    label: str
    importance: int
    target: int
    floor: int
    required: bool


@dataclass(frozen=True)
class SkillTarget:
    skill: str
    tier: str
    importance: int
    target_score: int
    floor_score: int
    required: bool


@dataclass(frozen=True)
class RoleProfile:
    profile_key: str
    name: str
    seniority: str
    config: Mapping[str, object]  # loop, components, tiers, tracks, gates, budgets, final simulation
    targets: tuple[SkillTarget, ...]


@dataclass(frozen=True)
class ProblemSkill:
    skill: str
    mapping_weight_bp: int


@dataclass(frozen=True)
class Problem:
    id: int
    platform: str
    platform_key: str
    title: str
    difficulty: str
    expected_minutes: int | None
    is_canonical: bool
    skills: tuple[ProblemSkill, ...]
    guide: Mapping[str, object] | None = (
        None  # pattern, complexity, hints, mistakes, prerequisites, relevance
    )


@dataclass(frozen=True)
class Milestone:
    key: str
    track: str
    track_position: int  # 1-based order of the track in roadmap.yaml
    position: int  # 1-based order within the track
    name: str
    skills: tuple[str, ...]
    extra_exit: tuple[str, ...] = ()
    content: str | None = None
    starts_when: str | None = None


@dataclass(frozen=True)
class BaselineItem:
    key: str
    position: int
    name: str
    minutes: int
    observation_kind: str
    covers: tuple[str, ...]


@dataclass(frozen=True)
class MissionTemplate:
    key: str
    component: str
    stages: tuple[str, ...]
    gap_types: tuple[str, ...] | None
    applies_to: tuple[str, ...] | None
    item_type: str | None
    minutes: int | None
    minutes_rule: str | None
    min_budget: int | None
    difficulty: str | None
    needs_problem: bool
    observation: Mapping[str, object]
    pass_rule: str
    partial_rule: str | None
    output_level: int
    next_on_pass: str | None
    next_on_fail: str | None


@dataclass(frozen=True)
class Catalog:
    seed_version: str
    groups: tuple[SkillGroup, ...]
    skills: tuple[Skill, ...]
    profiles: tuple[RoleProfile, ...]
    problems: tuple[Problem, ...]
    milestones: tuple[Milestone, ...]
    baseline: tuple[BaselineItem, ...]
    templates: tuple[MissionTemplate, ...]
    milestone_exit_rule: str = ""
    topological_order: tuple[str, ...] = field(default=())
    max_depth: int = 0
    learning: LearningCatalog = field(default_factory=LearningCatalog)
