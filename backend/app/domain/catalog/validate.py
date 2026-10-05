"""Seed validation: parsed YAML (plain dicts) -> typed ``Catalog`` or a list of issues.

Pure: no file or database access. Every rule here is a documented constraint of Spec v2
(SKILL_GRAPH §1-2, ROLE_PROFILE §3-9, ROADMAP §1, MISSION_LIBRARY §1, DATA_MODEL §2). Nothing is written to
the database unless this returns zero errors.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.domain.activity.vocabulary import PERSONAL_PROBLEM_ID_START
from app.domain.catalog import vocabulary as v
from app.domain.catalog.fingerprint import catalog_fingerprint, check_lock, file_fingerprints
from app.domain.catalog.graph import validate_graph
from app.domain.catalog.issues import Issue
from app.domain.catalog.model import (
    BaselineItem,
    Catalog,
    Milestone,
    MissionTemplate,
    Prerequisite,
    Problem,
    ProblemSkill,
    RoleProfile,
    Skill,
    SkillGroup,
    SkillTarget,
    TierSpec,
)
from app.domain.catalog.templates import resolve_template

FILE_NAMES = {
    "skill_graph": v.SEED_FILES["skill_graph"],
    "problem_catalog": v.SEED_FILES["problem_catalog"],
    "roadmap": v.SEED_FILES["roadmap"],
    "mission_templates": v.SEED_FILES["mission_templates"],
}


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[Issue, ...]
    catalog: Catalog | None
    file_fingerprints: Mapping[str, str] = field(default_factory=dict)
    catalog_fingerprint: str = ""

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.is_error)

    @property
    def ok(self) -> bool:
        return not self.errors and self.catalog is not None


class _Collector:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, code: str, where: str, message: str) -> None:
        self.issues.append(Issue(code, where, message))

    def require(self, record: Mapping[str, Any], key: str, kind: type | tuple[type, ...], where: str) -> Any:
        """Return record[key] if present and of ``kind`` (bool is never accepted as int), else report."""
        if key not in record or record[key] is None:
            self.error("seed.missing_field", where, f"missing required field {key!r}")
            return None
        value = record[key]
        kinds = kind if isinstance(kind, tuple) else (kind,)
        if isinstance(value, bool) and bool not in kinds:
            self.error("seed.wrong_type", where, f"{key!r} must be {_names(kinds)}, got a boolean")
            return None
        if not isinstance(value, kinds):
            self.error(
                "seed.wrong_type", where, f"{key!r} must be {_names(kinds)}, got {type(value).__name__}"
            )
            return None
        if isinstance(value, str) and not value.strip():
            self.error("seed.empty_field", where, f"{key!r} must not be empty")
            return None
        return value

    def optional(self, record: Mapping[str, Any], key: str, kind: type | tuple[type, ...], where: str) -> Any:
        if record.get(key) is None:
            return None
        return self.require(record, key, kind, where)


def _names(kinds: tuple[type, ...]) -> str:
    return " or ".join(k.__name__ for k in kinds)


def _score(c: _Collector, value: Any, where: str, field_name: str) -> bool:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        c.error("seed.invalid_score", where, f"{field_name} must be an integer 0-100, got {value!r}")
        return False
    return True


def _no_floats(c: _Collector, value: Any, where: str) -> None:
    if isinstance(value, float | Decimal):
        c.error(
            "seed.float_value", where, f"floats are not allowed in seed data (got {value!r}); use integers"
        )
    elif isinstance(value, Mapping):
        for k, item in value.items():
            _no_floats(c, item, f"{where}.{k}")
    elif isinstance(value, list | tuple):
        for i, item in enumerate(value):
            _no_floats(c, item, f"{where}[{i}]")


# --------------------------------------------------------------------------------------------- entry point


def validate_seed(raw: Mapping[str, Any], lock: Mapping[str, Any] | None) -> ValidationResult:
    """Validate the complete seed set. ``raw`` keys: skill_graph, problem_catalog, roadmap, mission_templates,
    and one ``role_profile:<file stem>`` per role-profile file."""
    c = _Collector()
    for role in ("skill_graph", "problem_catalog", "roadmap", "mission_templates"):
        if not isinstance(raw.get(role), Mapping):
            c.error("seed.missing_file", FILE_NAMES[role], "file is missing or not a YAML mapping")
    profile_roles = sorted(role for role in raw if role.startswith("role_profile:"))
    if not profile_roles:
        c.error("seed.missing_file", f"{v.ROLE_PROFILE_DIR}/*.yaml", "at least one role profile is required")
    if c.issues:
        return ValidationResult(tuple(c.issues), None)
    for role in raw:
        _no_floats(c, raw[role], _file_of(role))
    if c.issues:  # fingerprints (canonical JSON) are undefined for floats; report and stop here
        return ValidationResult(tuple(c.issues), None)

    seed_version = _seed_version(c, raw)
    groups, skills, graph_meta = _skills(c, raw["skill_graph"])
    skill_by_key = {s.key: s for s in skills}
    profiles = [_profile(c, role, raw[role], skill_by_key, graph_meta) for role in profile_roles]
    problems = _problems(c, raw["problem_catalog"], skill_by_key)
    milestones, baseline, exit_rule = _roadmap(c, raw["roadmap"], skill_by_key, groups, profiles)
    templates = _templates(c, raw["mission_templates"], skill_by_key)

    fingerprints = file_fingerprints(raw)
    combined = catalog_fingerprint(fingerprints)
    if seed_version is not None:
        c.issues.extend(check_lock(seed_version, fingerprints, lock or {}, lock_name=v.LOCK_FILE))

    if any(i.is_error for i in c.issues) or seed_version is None:
        return ValidationResult(tuple(c.issues), None, fingerprints, combined)
    catalog = Catalog(
        seed_version=seed_version,
        groups=tuple(groups),
        skills=tuple(skills),
        profiles=tuple(p for p in profiles if p is not None),
        problems=tuple(problems),
        milestones=tuple(milestones),
        baseline=tuple(baseline),
        templates=tuple(templates),
        milestone_exit_rule=exit_rule,
        topological_order=tuple(graph_meta["order"]),
        max_depth=int(graph_meta["max_depth"]),
    )
    return ValidationResult(tuple(c.issues), catalog, fingerprints, combined)


def _file_of(role: str) -> str:
    if role.startswith("role_profile:"):
        return f"{v.ROLE_PROFILE_DIR}/{role.split(':', 1)[1]}.yaml"
    return FILE_NAMES.get(role, role)


def _seed_version(c: _Collector, raw: Mapping[str, Any]) -> str | None:
    versions: dict[str, str] = {}
    for role in sorted(raw):
        value = raw[role].get("seed_version")
        if not isinstance(value, str) or not v.SEED_VERSION_PATTERN.match(value):
            c.error(
                "seed.invalid_version",
                _file_of(role),
                f"seed_version must look like 'seed-v1', got {value!r}",
            )
        else:
            versions[role] = value
    distinct = sorted(set(versions.values()))
    if len(distinct) > 1:
        detail = ", ".join(f"{_file_of(r)}={ver}" for r, ver in sorted(versions.items()))
        c.error("seed.version_mismatch", "seed/", f"all seed files must share one seed_version: {detail}")
        return None
    return distinct[0] if distinct and len(versions) == len(raw) else None


# --------------------------------------------------------------------------------------------- skills


def _skills(c: _Collector, data: Mapping[str, Any]) -> tuple[list[SkillGroup], list[Skill], dict[str, Any]]:
    f = FILE_NAMES["skill_graph"]
    groups: list[SkillGroup] = []
    for i, g in enumerate(c.require(data, "groups", list, f) or []):
        where = f"{f}: groups[{i}]"
        if not isinstance(g, Mapping):
            c.error("seed.wrong_type", where, "each group must be a mapping")
            continue
        key, name, comp = (c.require(g, k, str, where) for k in ("key", "name", "component"))
        if comp is not None and comp not in v.COMPONENTS:
            c.error("skills.invalid_component", where, f"unknown component {comp!r}; allowed: {v.COMPONENTS}")
        elif key and name:
            groups.append(SkillGroup(key, name, comp))
    for key, count in Counter(g.key for g in groups).items():
        if count > 1:
            c.error("skills.duplicate_group", f"{f}: groups", f"group key {key!r} appears {count} times")
    group_by_key = {g.key: g for g in groups}

    skills: list[Skill] = []
    edges: dict[str, list[str]] = {}
    for i, s in enumerate(c.require(data, "skills", list, f) or []):
        where = f"{f}: skills[{i}]"
        if not isinstance(s, Mapping):
            c.error("seed.wrong_type", where, "each skill must be a mapping")
            continue
        key = c.require(s, "key", str, where)
        if key is None:
            continue
        where = f"{f}: skills[{key}]"
        if not v.SKILL_KEY_PATTERN.match(key):
            c.error(
                "skills.invalid_key", where, "skill keys are lowercase dotted identifiers, e.g. 'graph.bfs'"
            )
        if key in group_by_key:
            c.error("skills.key_is_group", where, f"{key!r} is also a group key")
        name = c.require(s, "name", str, where)
        parent = c.require(s, "parent", str, where)
        comp = c.require(s, "component", str, where)
        is_pattern = c.require(s, "is_pattern", bool, where)
        kinds = c.require(s, "evidence_kinds", list, where) or []
        prereqs_raw = s.get("prerequisites", [])
        topics = c.optional(s, "topics", list, where) or []
        if parent is not None and parent not in group_by_key:
            c.error("skills.missing_parent", where, f"parent group {parent!r} does not exist")
        if comp is not None and comp not in v.COMPONENTS:
            c.error("skills.invalid_component", where, f"unknown component {comp!r}; allowed: {v.COMPONENTS}")
        elif parent in group_by_key and comp != group_by_key[parent].component:
            c.error(
                "skills.component_mismatch",
                where,
                f"component {comp!r} differs from its group's component {group_by_key[parent].component!r}",
            )
        for kind in kinds:
            if kind not in v.EVIDENCE_KINDS:
                c.error("skills.invalid_evidence_kind", where, f"unknown evidence kind {kind!r}")
        prereqs: list[Prerequisite] = []
        if not isinstance(prereqs_raw, list):
            c.error("seed.wrong_type", where, "'prerequisites' must be a list")
            prereqs_raw = []
        for j, p in enumerate(prereqs_raw):
            pwhere = f"{where}.prerequisites[{j}]"
            if not isinstance(p, Mapping):
                c.error("seed.wrong_type", pwhere, "each prerequisite must be {skill, min_score}")
                continue
            pkey = c.require(p, "skill", str, pwhere)
            min_score = c.require(p, "min_score", int, pwhere)
            if min_score is not None and min_score not in v.ALLOWED_MIN_SCORES:
                c.error(
                    "skills.invalid_min_score", pwhere, f"min_score must be one of {v.ALLOWED_MIN_SCORES}"
                )
            if pkey is not None and min_score is not None:
                prereqs.append(Prerequisite(pkey, min_score))
        edges[key] = [p.skill for p in prereqs]
        if None not in (name, parent, comp, is_pattern):
            skills.append(
                Skill(
                    key,
                    name,
                    parent,
                    comp,
                    is_pattern,
                    tuple(prereqs),
                    tuple(kinds),
                    tuple(str(t) for t in topics),
                )
            )
    for key, count in Counter(s.key for s in skills).items():
        if count > 1:
            c.error("skills.duplicate_key", f"{f}: skills[{key}]", f"skill key {key!r} appears {count} times")

    # Graph checks that need tiers (required vs optional) run in _profile; here: structure + cycles + depth.
    order_nodes = [s.key for s in skills]
    report = validate_graph(order_nodes, edges, max_depth=v.MAX_PREREQUISITE_DEPTH, source=f)
    c.issues.extend(report.issues)
    meta: dict[str, Any] = {"order": report.topological_order, "max_depth": report.max_depth, "edges": edges}
    return groups, skills, meta


# --------------------------------------------------------------------------------------------- role profile


def _profile(
    c: _Collector, role: str, data: Mapping[str, Any], skills: Mapping[str, Skill], graph: Mapping[str, Any]
) -> RoleProfile | None:
    f = _file_of(role)
    key = c.require(data, "profile_key", str, f)
    name = c.require(data, "name", str, f)
    seniority = c.require(data, "seniority", str, f)
    if key is not None and f"{v.ROLE_PROFILE_DIR}/{key}.yaml" != f:
        c.error("profile.key_mismatch", f, f"profile_key {key!r} must match the file name")

    # components
    components = c.require(data, "components", list, f) or []
    comp_keys = [comp.get("key") for comp in components if isinstance(comp, Mapping)]
    if sorted(k for k in comp_keys if k) != sorted(v.COMPONENTS) or len(comp_keys) != len(v.COMPONENTS):
        c.error("profile.components", f"{f}: components", f"must define each of {v.COMPONENTS} exactly once")
    weight_sum = 0
    for comp in components:
        where = f"{f}: components[{comp.get('key')}]" if isinstance(comp, Mapping) else f"{f}: components"
        if not isinstance(comp, Mapping):
            c.error("seed.wrong_type", where, "each component must be a mapping")
            continue
        weight, gate, stretch = (c.require(comp, k, int, where) for k in ("weight", "gate", "stretch"))
        for label, value in (("weight", weight), ("gate", gate), ("stretch", stretch)):
            if value is not None:
                _score(c, value, where, label)
        if isinstance(weight, int):
            weight_sum += weight
        if isinstance(gate, int) and isinstance(stretch, int) and stretch < gate:
            c.error("profile.stretch_below_gate", where, f"stretch {stretch} must be >= gate {gate}")
    if weight_sum != 100:
        c.error("profile.weights", f"{f}: components", f"component weights must sum to 100, got {weight_sum}")

    # tiers
    tiers_raw = c.require(data, "tiers", Mapping, f) or {}
    tiers: dict[str, TierSpec] = {}
    if sorted(tiers_raw) != sorted(v.TIERS):
        c.error("profile.tiers", f"{f}: tiers", f"must define exactly {v.TIERS}")
    for tier, spec in tiers_raw.items():
        where = f"{f}: tiers.{tier}"
        if not isinstance(spec, Mapping):
            c.error("seed.wrong_type", where, "tier must be a mapping")
            continue
        label = c.require(spec, "label", str, where)
        values = {k: c.require(spec, k, int, where) for k in ("importance", "target", "floor")}
        required = c.require(spec, "required", bool, where)
        if not all(_score(c, val, where, k) for k, val in values.items() if val is not None):
            continue
        if None in values.values() or required is None or label is None:
            continue
        if values["floor"] > values["target"]:
            c.error(
                "profile.floor_above_target", where, f"floor {values['floor']} > target {values['target']}"
            )
        if required and values["target"] <= 0:
            c.error("profile.required_target", where, "a required tier must have a positive target")
        tiers[tier] = TierSpec(tier, label, values["importance"], values["target"], values["floor"], required)

    # skill tiers
    targets: list[SkillTarget] = []
    tier_of: dict[str, str] = {}
    tier_lists = c.require(data, "skill_tiers", Mapping, f) or {}
    for tier, keys in tier_lists.items():
        where = f"{f}: skill_tiers.{tier}"
        if tier not in v.TIERS:
            c.error("profile.unknown_tier", where, f"unknown tier {tier!r}")
            continue
        if not isinstance(keys, list):
            c.error("seed.wrong_type", where, "must be a list of skill keys")
            continue
        for skill_key in keys:
            if skill_key not in skills:
                c.error("profile.unknown_skill", where, f"role references unknown skill {skill_key!r}")
            elif skill_key in tier_of:
                c.error(
                    "profile.duplicate_skill",
                    where,
                    f"{skill_key!r} is listed in both {tier_of[skill_key]} and {tier}",
                )
            else:
                tier_of[skill_key] = tier
    for skill_key in skills:
        if skill_key not in tier_of:
            c.error("profile.missing_skill", f"{f}: skill_tiers", f"skill {skill_key!r} has no tier")
    for skill_key in skills:
        spec = tiers.get(tier_of.get(skill_key, ""))
        if spec is not None:
            targets.append(
                SkillTarget(skill_key, spec.tier, spec.importance, spec.target, spec.floor, spec.required)
            )

    # graph rules that depend on tiers
    if len(tiers) == len(v.TIERS) and len(tier_of) == len(skills):  # only when every tier and skill is valid
        optional = frozenset(k for k, t in tier_of.items() if t in tiers and not tiers[t].required)
        report = validate_graph(
            list(skills), graph["edges"], optional_nodes=optional, source=v.SEED_FILES["skill_graph"]
        )
        c.issues.extend(i for i in report.issues if i.code == "graph.required_depends_on_optional")
        target_of = {t.skill: t.target_score for t in targets}
        for skill in skills.values():
            for p in skill.prerequisites:
                if p.skill in target_of and p.min_score > target_of[p.skill]:
                    c.error(
                        "profile.unreachable_prerequisite",
                        f"{v.SEED_FILES['skill_graph']}: skills[{skill.key}].prerequisites",
                        f"min_score {p.min_score} on {p.skill} exceeds its target "
                        f"{target_of[p.skill]} in {key}",
                    )
        _gate_vs_target_mean(c, f, components, skills, targets)

    _tracks_and_budgets(c, f, data, comp_keys)
    _loop(c, f, data)
    for k in ("gate_parameters", "final_simulation"):
        c.require(data, k, Mapping, f)

    if c.issues and any(i.is_error and i.where.startswith(f) for i in c.issues):
        return None
    if key is None or name is None or seniority is None:
        return None
    config = {k: val for k, val in data.items() if k not in ("skill_tiers", "seed_version")}
    return RoleProfile(key, name, seniority, config, tuple(targets))


def _gate_vs_target_mean(
    c: _Collector,
    f: str,
    components: Sequence[Any],
    skills: Mapping[str, Skill],
    targets: Sequence[SkillTarget],
) -> None:
    by_skill = {t.skill: t for t in targets}
    for comp in components:
        if not isinstance(comp, Mapping) or not isinstance(comp.get("gate"), int):
            continue
        required = [
            by_skill[s.key]
            for s in skills.values()
            if s.component == comp["key"] and by_skill[s.key].required
        ]
        if not required:
            c.error(
                "profile.empty_component",
                f"{f}: components[{comp['key']}]",
                "component has no required skills",
            )
            continue
        total_importance = sum(t.importance for t in required)
        weighted = sum(t.importance * t.target_score for t in required)
        # gate <= weighted mean  <=>  gate * total_importance <= weighted  (integer arithmetic)
        if comp["gate"] * total_importance > weighted:
            c.error(
                "profile.gate_above_target_mean",
                f"{f}: components[{comp['key']}]",
                f"gate {comp['gate']} exceeds the importance-weighted target mean "
                f"{Decimal(weighted) / Decimal(total_importance):.2f}; all-at-target could never pass",
            )


def _tracks_and_budgets(c: _Collector, f: str, data: Mapping[str, Any], comp_keys: Sequence[Any]) -> None:
    tracks = c.require(data, "tracks", Mapping, f) or {}
    total = 0
    seen: dict[str, str] = {}
    for track, spec in tracks.items():
        where = f"{f}: tracks.{track}"
        if not isinstance(spec, Mapping):
            c.error("seed.wrong_type", where, "track must be a mapping")
            continue
        minutes = c.require(spec, "minutes", int, where)
        total += minutes if isinstance(minutes, int) else 0
        for comp in c.require(spec, "components", list, where) or []:
            if comp not in v.COMPONENTS:
                c.error("profile.unknown_component", where, f"unknown component {comp!r}")
            elif comp in seen:
                c.error("profile.component_in_two_tracks", where, f"{comp} is already in track {seen[comp]}")
            else:
                seen[comp] = track
    for comp in comp_keys:
        if comp in v.COMPONENTS and comp not in seen:
            c.error("profile.component_without_track", f"{f}: tracks", f"component {comp!r} has no track")
    if total > v.WEEKLY_MINUTES:
        c.error("profile.track_minutes", f"{f}: tracks", f"track minutes sum to {total} > {v.WEEKLY_MINUTES}")
    budgets = c.require(data, "weekday_budgets_default", list, f)
    if budgets is not None:
        if len(budgets) != 7 or not all(
            isinstance(b, int) and not isinstance(b, bool) and b >= 0 for b in budgets
        ):
            c.error(
                "profile.weekday_budgets", f"{f}: weekday_budgets_default", "need 7 non-negative integers"
            )
        elif sum(budgets) != v.WEEKLY_MINUTES:
            c.error(
                "profile.weekday_budgets",
                f"{f}: weekday_budgets_default",
                f"weekday budgets sum to {sum(budgets)}, expected {v.WEEKLY_MINUTES}",
            )


def _loop(c: _Collector, f: str, data: Mapping[str, Any]) -> None:
    for i, rnd in enumerate(c.require(data, "interview_loop", list, f) or []):
        where = f"{f}: interview_loop[{i}]"
        if not isinstance(rnd, Mapping):
            c.error("seed.wrong_type", where, "round must be a mapping")
            continue
        rt = rnd.get("round_type")
        if rt is not None and rt not in v.ROUND_TYPES:
            c.error("profile.unknown_round_type", where, f"unknown round_type {rt!r}")
        for comp in rnd.get("components", []):
            if comp not in v.COMPONENTS:
                c.error("profile.unknown_component", where, f"unknown component {comp!r}")
    final = data.get("final_simulation")
    if isinstance(final, Mapping):
        for k in ("required_round_types", "one_of_round_types"):
            for rt in final.get(k, []):
                if rt not in v.ROUND_TYPES:
                    c.error("profile.unknown_round_type", f"{f}: final_simulation.{k}", f"unknown {rt!r}")


# --------------------------------------------------------------------------------------------- problems


def _problems(c: _Collector, data: Mapping[str, Any], skills: Mapping[str, Skill]) -> list[Problem]:
    f = FILE_NAMES["problem_catalog"]
    out: list[Problem] = []
    for i, p in enumerate(c.require(data, "problems", list, f) or []):
        where = f"{f}: problems[{i}]"
        if not isinstance(p, Mapping):
            c.error("seed.wrong_type", where, "each problem must be a mapping")
            continue
        pid = c.require(p, "id", int, where)
        where = f"{f}: problems[id={pid}]" if pid is not None else where
        platform = c.require(p, "platform", str, where)
        pkey = c.require(p, "platform_key", str, where)
        title = c.require(p, "title", str, where)
        difficulty = c.require(p, "difficulty", str, where)
        canonical = c.require(p, "is_canonical", bool, where)
        expected = c.optional(p, "expected_minutes", int, where)
        if pid is not None and not 0 < pid < PERSONAL_PROBLEM_ID_START:
            c.error(
                "problems.invalid_id",
                where,
                f"seed problem ids must be between 1 and {PERSONAL_PROBLEM_ID_START - 1} "
                "(higher ids are personal problems)",
            )
        if platform is not None and platform not in v.PLATFORMS:
            c.error("problems.invalid_platform", where, f"platform must be one of {v.PLATFORMS}")
        if difficulty is not None and difficulty not in v.DIFFICULTIES:
            c.error("problems.invalid_difficulty", where, f"difficulty must be one of {v.DIFFICULTIES}")
        if expected is not None and expected <= 0:
            c.error("problems.invalid_expected_minutes", where, "expected_minutes must be positive")
        mappings: list[ProblemSkill] = []
        for j, m in enumerate(c.require(p, "skills", list, where) or []):
            mwhere = f"{where}.skills[{j}]"
            if not isinstance(m, Mapping):
                c.error("seed.wrong_type", mwhere, "mapping must be {skill, mapping_weight_bp}")
                continue
            skill = c.require(m, "skill", str, mwhere)
            weight = c.require(m, "mapping_weight_bp", int, mwhere)
            if skill is not None and skill not in skills:
                c.error("problems.unknown_skill", mwhere, f"unknown skill {skill!r}")
            if weight is not None and weight not in v.MAPPING_WEIGHTS_BP:
                c.error(
                    "problems.invalid_weight",
                    mwhere,
                    f"mapping_weight_bp must be one of {v.MAPPING_WEIGHTS_BP}",
                )
            if skill is not None and weight is not None:
                mappings.append(ProblemSkill(skill, weight))
        primaries = [m for m in mappings if m.mapping_weight_bp == v.PRIMARY_MAPPING_BP]
        if len(primaries) != 1:
            c.error(
                "problems.primary_mapping",
                where,
                f"exactly one primary (10000) mapping required, got {len(primaries)}",
            )
        for skill, count in Counter(m.skill for m in mappings).items():
            if count > 1:
                c.error("problems.duplicate_mapping", where, f"skill {skill!r} mapped {count} times")
        if None not in (pid, platform, pkey, title, difficulty, canonical):
            out.append(Problem(pid, platform, pkey, title, difficulty, expected, canonical, tuple(mappings)))
    for pid, count in Counter(p.id for p in out).items():
        if count > 1:
            c.error("problems.duplicate_id", f"{f}: problems", f"problem id {pid} appears {count} times")
    for ident, count in Counter((p.platform, p.platform_key) for p in out).items():
        if count > 1:
            c.error(
                "problems.duplicate_identity",
                f"{f}: problems",
                f"{ident[0]}/{ident[1]} appears {count} times",
            )
    return out


# --------------------------------------------------------------------------------------------- roadmap


def _roadmap(
    c: _Collector,
    data: Mapping[str, Any],
    skills: Mapping[str, Skill],
    groups: Sequence[SkillGroup],
    profiles: Sequence[RoleProfile | None],
) -> tuple[list[Milestone], list[BaselineItem], str]:
    f = FILE_NAMES["roadmap"]
    exit_rule = c.require(data, "milestone_exit_rule", str, f) or ""
    milestones: list[Milestone] = []
    placed: dict[str, tuple[str, int, str]] = {}
    tracks = c.require(data, "tracks", Mapping, f) or {}
    profile_tracks: set[str] = set()
    for profile in profiles:
        tracks_config = profile.config.get("tracks") if profile is not None else None
        if isinstance(tracks_config, Mapping):
            profile_tracks.update(str(t) for t in tracks_config)
    if profile_tracks and set(tracks) != profile_tracks:
        c.error(
            "roadmap.tracks_mismatch",
            f"{f}: tracks",
            f"roadmap tracks {sorted(tracks)} must equal role-profile tracks {sorted(profile_tracks)}",
        )
    for track_position, (track, items) in enumerate(tracks.items(), start=1):
        if not isinstance(items, list) or not items:
            c.error(
                "roadmap.missing_milestone", f"{f}: tracks.{track}", "a track needs at least one milestone"
            )
            continue
        for position, m in enumerate(items, start=1):
            where = f"{f}: tracks.{track}[{position - 1}]"
            if not isinstance(m, Mapping):
                c.error("seed.wrong_type", where, "milestone must be a mapping")
                continue
            key = c.require(m, "key", str, where)
            name = c.require(m, "name", str, where)
            keys = m.get("skills")
            if not isinstance(keys, list):
                c.error("seed.missing_field", where, "missing required field 'skills' (may be an empty list)")
                keys = []
            where = f"{f}: milestones[{key}]"
            for skill in keys:
                if skill not in skills:
                    c.error("roadmap.unknown_skill", where, f"unknown skill {skill!r}")
                elif skill in placed:
                    c.error(
                        "roadmap.duplicate_skill",
                        where,
                        f"{skill} is already in milestone {placed[skill][2]}",
                    )
                else:
                    placed[skill] = (track, position, key or "?")
            extra = m.get("extra_exit", [])
            if key and name:
                milestones.append(
                    Milestone(
                        key,
                        track,
                        track_position,
                        position,
                        name,
                        tuple(keys),
                        tuple(str(x) for x in extra),
                        m.get("content"),
                        m.get("starts_when"),
                    )
                )
    for key, count in Counter(m.key for m in milestones).items():
        if count > 1:
            c.error(
                "roadmap.duplicate_milestone",
                f"{f}: milestones",
                f"milestone key {key!r} appears {count} times",
            )
    for skill in skills:
        if skill not in placed:
            c.error("roadmap.missing_skill", f"{f}: tracks", f"skill {skill!r} is in no milestone")
    # Ordering: within one track, a skill must not need a prerequisite introduced in a LATER milestone.
    for skill_key, (track, position, mkey) in placed.items():
        for p in skills[skill_key].prerequisites:
            other = placed.get(p.skill)
            if other and other[0] == track and other[1] > position:
                c.error(
                    "roadmap.ordering",
                    f"{f}: milestones[{mkey}]",
                    f"{skill_key} ({mkey}) requires {p.skill}, which is introduced later in {other[2]}",
                )

    baseline: list[BaselineItem] = []
    block = c.require(data, "baseline", Mapping, f) or {}
    group_keys = {g.key for g in groups}
    for position, item in enumerate(c.require(block, "items", list, f"{f}: baseline") or [], start=1):
        where = f"{f}: baseline.items[{position - 1}]"
        if not isinstance(item, Mapping):
            c.error("seed.wrong_type", where, "battery item must be a mapping")
            continue
        key = c.require(item, "key", str, where)
        name = c.require(item, "name", str, where)
        minutes = c.require(item, "minutes", int, where)
        kind = c.require(item, "observation", str, where)
        covers = c.require(item, "covers", list, where) or []
        if minutes is not None and minutes <= 0:
            c.error("roadmap.invalid_minutes", where, "minutes must be positive")
        if kind is not None and kind not in v.OBSERVATION_KINDS:
            c.error("roadmap.invalid_observation", where, f"unknown observation kind {kind!r}")
        for cover in covers:
            if cover != "all required" and cover not in group_keys:
                c.error("roadmap.unknown_group", where, f"covers unknown skill group {cover!r}")
        if None not in (key, name, minutes, kind):
            baseline.append(BaselineItem(key, position, name, minutes, kind, tuple(covers)))
    for key, count in Counter(b.key for b in baseline).items():
        if count > 1:
            c.error("roadmap.duplicate_battery_item", f"{f}: baseline", f"item {key!r} appears {count} times")
    total = block.get("total_minutes")
    if isinstance(total, int) and total != sum(b.minutes for b in baseline):
        c.error(
            "roadmap.battery_total", f"{f}: baseline.total_minutes", "does not equal the sum of item minutes"
        )
    return milestones, baseline, exit_rule


# --------------------------------------------------------------------------------------------- templates


def _templates(c: _Collector, data: Mapping[str, Any], skills: Mapping[str, Skill]) -> list[MissionTemplate]:
    f = FILE_NAMES["mission_templates"]
    out: list[MissionTemplate] = []
    for i, t in enumerate(c.require(data, "templates", list, f) or []):
        where = f"{f}: templates[{i}]"
        if not isinstance(t, Mapping):
            c.error("seed.wrong_type", where, "template must be a mapping")
            continue
        key = c.require(t, "key", str, where)
        where = f"{f}: templates[{key}]"
        comp = c.require(t, "component", str, where)
        stage_raw = c.require(t, "stage", (str, list), where)
        stages = tuple([stage_raw] if isinstance(stage_raw, str) else (stage_raw or []))
        pass_rule = c.require(t, "pass_rule", str, where)
        output_level = c.require(t, "output_level", int, where)
        observation = c.require(t, "observation", Mapping, where)
        if comp is not None and comp not in v.TEMPLATE_COMPONENTS:
            c.error("templates.unknown_component", where, f"unknown component {comp!r}")
        if comp is not None and key is not None and not key.startswith(f"{comp}."):
            c.error("templates.key_prefix", where, f"key must start with '{comp}.'")
        for stage in stages:
            if stage not in v.STAGES:
                c.error("templates.unknown_stage", where, f"unknown stage {stage!r}")
        if not stages:
            c.error("templates.unknown_stage", where, "at least one stage is required")
        gap_types = t.get("gap_types")
        if gap_types is not None:
            for gt in gap_types:
                if gt not in v.GAP_TYPES:
                    c.error("templates.unknown_gap_type", where, f"unknown gap type {gt!r}")
        applies_to = t.get("applies_to")
        if applies_to is not None:
            for target in applies_to:
                matched = [
                    s for s in skills if (s.startswith(target) if target.endswith(".") else s == target)
                ]
                if not matched:
                    c.error("templates.unknown_skill", where, f"applies_to {target!r} matches no skill")
                elif comp in v.COMPONENTS and any(skills[s].component != comp for s in matched):
                    c.error(
                        "templates.component_mismatch",
                        where,
                        f"applies_to {target!r} reaches another component",
                    )
        minutes = t.get("minutes")
        minutes_rule = t.get("minutes_rule")
        if minutes is None and minutes_rule is None:
            c.error("templates.invalid_duration", where, "needs minutes (positive int) or minutes_rule")
        if minutes is not None and (
            not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0
        ):
            c.error(
                "templates.invalid_duration", where, f"minutes must be a positive integer, got {minutes!r}"
            )
        if minutes_rule is not None and comp not in ("revision", "mock"):
            c.error(
                "templates.invalid_duration",
                where,
                "minutes_rule is only allowed for revision/mock templates",
            )
        min_budget = t.get("min_budget")
        if min_budget is not None and (
            not isinstance(min_budget, int) or (isinstance(minutes, int) and min_budget < minutes)
        ):
            c.error("templates.invalid_duration", where, "min_budget must be an integer >= minutes")
        difficulty = t.get("difficulty")
        if difficulty is not None and difficulty not in v.DIFFICULTIES:
            c.error("templates.invalid_difficulty", where, f"unknown difficulty {difficulty!r}")
        if output_level is not None and not 0 <= output_level <= 7:
            c.error("templates.invalid_level", where, "output_level must be 0-7")
        item_type = t.get("item_type")
        if comp == "revision" and item_type not in v.REVISION_ITEM_TYPES:
            c.error(
                "templates.invalid_item_type",
                where,
                f"revision templates need item_type in {v.REVISION_ITEM_TYPES}",
            )
        if comp != "revision" and item_type is not None:
            c.error("templates.invalid_item_type", where, "item_type is only allowed on revision templates")
        for nxt_key in ("next_on_pass", "next_on_fail"):
            nxt = t.get(nxt_key)
            if nxt is not None and nxt not in v.NEXT_STAGE_TOKENS:
                c.error(
                    "templates.broken_reference",
                    where,
                    f"{nxt_key} {nxt!r} is not a stage or GAP_ENGINE/MOCK",
                )
            if nxt is None and comp in v.COMPONENTS:
                c.error("templates.broken_reference", where, f"{nxt_key} is required for skill templates")
        if isinstance(observation, Mapping):
            kinds = observation.get("kind")
            kind_list: list[object] = list(kinds) if isinstance(kinds, list) else [kinds]
            for kind in kind_list:
                if kind not in v.OBSERVATION_KINDS:
                    c.error("templates.unknown_observation", where, f"unknown observation kind {kind!r}")
        if None in (key, comp, pass_rule, output_level, observation) or not stages:
            continue
        out.append(
            MissionTemplate(
                key=key,
                component=comp,
                stages=stages,
                gap_types=tuple(gap_types) if gap_types is not None else None,
                applies_to=tuple(applies_to) if applies_to is not None else None,
                item_type=item_type,
                minutes=minutes if isinstance(minutes, int) else None,
                minutes_rule=minutes_rule,
                min_budget=min_budget,
                difficulty=difficulty,
                needs_problem=bool(t.get("needs_problem", False)),
                observation=observation,
                pass_rule=pass_rule,
                partial_rule=t.get("partial_rule"),
                output_level=output_level,
                next_on_pass=t.get("next_on_pass"),
                next_on_fail=t.get("next_on_fail"),
            )
        )
    for key, count in Counter(t.key for t in out).items():
        if count > 1:
            c.error(
                "templates.duplicate_key", f"{f}: templates", f"template key {key!r} appears {count} times"
            )
    # Coverage: every component's skills resolve a template for every stage the gap engine can recommend.
    for comp in v.COMPONENTS:
        sample = next((s for s in skills.values() if s.component == comp), None)
        if sample is None:
            continue
        for stage in v.GAP_STAGES:
            if resolve_template(out, component=comp, stage=stage, skill_key="~no.skill~") is None:
                c.error(
                    "templates.coverage", f"{f}", f"no template resolves component {comp!r} stage {stage}"
                )
    return out
