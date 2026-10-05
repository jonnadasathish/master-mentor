"""Catalog read service: assembles read models from the repository. No user state, no engine logic."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from typing import Any

from app.domain.catalog import vocabulary as v
from app.domain.catalog.model import MissionTemplate as DomainTemplate
from app.domain.catalog.templates import resolve_template
from app.errors import AppError
from app.models import MissionTemplate, Problem, RoleProfile, Skill
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.catalog import (
    BaselineItemOut,
    CatalogFile,
    CatalogSummary,
    CatalogVersions,
    ComponentNode,
    GroupNode,
    MilestoneOut,
    MilestoneRef,
    PrerequisiteListing,
    ProblemOut,
    ProblemSkillOut,
    RoadmapOut,
    RoleProfileOut,
    SkillDetail,
    SkillRef,
    SkillSummary,
    SkillTarget,
    TemplateOut,
    TemplateResolutionOut,
    TrackOut,
)
from app.schemas.envelope import ErrorCode

VERSION_ROLES = {
    "skill_graph_version": "skill_graph",
    "problem_catalog_version": "problem_catalog",
    "mission_template_version": "mission_templates",
    "roadmap_version": "roadmap",
}


def _not_found(what: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, f"{what} not found in the loaded catalog.", 404)


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repo = repository

    # ---------------------------------------------------------------------------------- version
    def seed_version(self) -> str:
        load = self._repo.current_load()
        if load is None:
            raise AppError(
                ErrorCode.INVALID_STATE,
                "The catalog is not loaded. Run `make seed`.",
                409,
                {"catalog": "empty"},
            )
        return load.seed_version

    def summary(self) -> CatalogSummary:
        self.seed_version()
        load = self._repo.current_load()
        assert load is not None
        files = dict(sorted(load.file_fingerprints_json.items()))

        def version(fingerprint: str) -> str:
            return f"{load.seed_version}+{fingerprint[:12]}"

        profile_fps = [fp for role, fp in files.items() if role.startswith("role_profile:")]
        versions = CatalogVersions(
            catalog_version=version(load.catalog_fingerprint),
            role_profile_version=version(profile_fps[0]) if len(profile_fps) == 1 else load.seed_version,
            **{name: version(files[role]) for name, role in VERSION_ROLES.items()},
        )
        return CatalogSummary(
            seed_version=load.seed_version,
            catalog_fingerprint=load.catalog_fingerprint,
            loaded_at=load.loaded_at.replace(tzinfo=UTC),  # stored as naive UTC
            versions=versions,
            files=[CatalogFile(role=role, fingerprint=fp) for role, fp in files.items()],
            counts=self._repo.counts(),
        )

    # ---------------------------------------------------------------------------------- skills
    def _targets_by_skill(self) -> tuple[RoleProfile, dict[int, tuple[str, int, int, int, bool]]]:
        profile = self.active_profile_row()
        required = _required_tiers(profile.config_json)
        return profile, {
            t.skill_id: (t.tier, t.importance, t.target_score, t.floor_score, required.get(t.tier, False))
            for t, _ in self._repo.targets(profile.id)
        }

    def _summary(
        self, skill: Skill, group: str, targets: Mapping[int, Any], prereq_count: int
    ) -> SkillSummary:
        tier, importance, target, floor, required = targets.get(skill.id, (None, None, None, None, None))
        return SkillSummary(
            key=skill.skill_key,
            name=skill.name,
            group=group,
            component=skill.component,
            is_pattern=skill.is_pattern,
            active=skill.active,
            tier=tier,
            importance=importance,
            target_score=target,
            floor_score=floor,
            required=required,
            prerequisite_count=prereq_count,
        )

    def skills(
        self, *, component: str | None = None, group: str | None = None, tier: str | None = None
    ) -> list[SkillSummary]:
        self.seed_version()
        if component is not None and component not in v.COMPONENTS:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown component {component!r}", 422)
        _, targets = self._targets_by_skill()
        counts: dict[str, int] = {}
        for skill_key, _, _ in self._repo.prerequisite_edges():
            counts[skill_key] = counts.get(skill_key, 0) + 1
        out = [
            self._summary(skill, group_key, targets, counts.get(skill.skill_key, 0))
            for skill, group_key in self._repo.skills(component=component, group_key=group)
        ]
        return [s for s in out if tier is None or s.tier == tier]

    def skill(self, skill_key: str) -> SkillDetail:
        self.seed_version()
        found = self._repo.skill(skill_key)
        if found is None:
            raise _not_found(f"Skill {skill_key!r}")
        skill, group_key = found
        _, targets = self._targets_by_skill()
        prereqs = self._repo.prerequisites(skill.id)
        milestone = self._repo.milestone_of_skill(skill.id)
        return SkillDetail(
            **self._summary(skill, group_key, targets, len(prereqs)).model_dump(),
            evidence_kinds=list(skill.evidence_kinds),
            topics=list(skill.topics),
            prerequisites=[SkillRef(key=p.skill_key, name=p.name, min_score=m) for p, m in prereqs],
            dependents=[
                SkillRef(key=d.skill_key, name=d.name, min_score=m)
                for d, m in self._repo.dependents(skill.id)
            ],
            milestone=MilestoneRef(key=milestone.milestone_key, name=milestone.name, track=milestone.track)
            if milestone
            else None,
            problem_count=len(self._repo.problems(skill_key=skill_key)),
        )

    def prerequisites(self, skill_key: str, *, transitive: bool = False) -> PrerequisiteListing:
        self.seed_version()
        if self._repo.skill(skill_key) is None:
            raise _not_found(f"Skill {skill_key!r}")
        edges: dict[str, list[tuple[str, int]]] = {}
        for key, prereq, min_score in self._repo.prerequisite_edges():
            edges.setdefault(key, []).append((prereq, min_score))
        names = {s.skill_key: s.name for s, _ in self._repo.skills(include_inactive=True)}
        refs: list[SkillRef] = []
        seen: set[str] = set()
        frontier = [(skill_key, 0)]
        while frontier:  # breadth-first: direct prerequisites first, then theirs (deterministic seed order)
            current, depth = frontier.pop(0)
            for prereq, min_score in edges.get(current, []):
                if prereq in seen:
                    continue
                seen.add(prereq)
                refs.append(SkillRef(key=prereq, name=names[prereq], min_score=min_score, depth=depth + 1))
                if transitive:
                    frontier.append((prereq, depth + 1))
        return PrerequisiteListing(skill=skill_key, transitive=transitive, prerequisites=refs)

    def dependents(self, skill_key: str) -> list[SkillRef]:
        self.seed_version()
        found = self._repo.skill(skill_key)
        if found is None:
            raise _not_found(f"Skill {skill_key!r}")
        return [
            SkillRef(key=d.skill_key, name=d.name, min_score=m) for d, m in self._repo.dependents(found[0].id)
        ]

    def tree(self) -> list[ComponentNode]:
        self.seed_version()
        by_group: dict[str, list[str]] = {}
        for skill, group_key in self._repo.skills():
            by_group.setdefault(group_key, []).append(skill.skill_key)
        nodes: dict[str, list[GroupNode]] = {}
        for group in self._repo.groups():
            nodes.setdefault(group.component, []).append(
                GroupNode(
                    key=group.group_key,
                    name=group.name,
                    component=group.component,
                    skills=by_group.get(group.group_key, []),
                )
            )
        return [ComponentNode(component=c, groups=nodes.get(c, [])) for c in v.COMPONENTS]

    def group_children(self, group_key: str) -> list[SkillSummary]:
        self.seed_version()
        if self._repo.group(group_key) is None:
            raise _not_found(f"Skill group {group_key!r}")
        return self.skills(group=group_key)

    # ---------------------------------------------------------------------------------- role profile
    def active_profile_row(self, profile_key: str | None = None) -> RoleProfile:
        """Until goals exist (Slice 5) the active profile is the single loaded one (D-045)."""
        if profile_key is not None:
            profile = self._repo.profile(profile_key)
            if profile is None:
                raise _not_found(f"Role profile {profile_key!r}")
            return profile
        profiles = self._repo.profiles()
        if len(profiles) != 1:
            raise AppError(
                ErrorCode.INVALID_STATE,
                "Several role profiles are loaded; pass profile_key "
                "(goal-based selection arrives with goals).",
                409,
                {"profiles": [p.profile_key for p in profiles]},
            )
        return profiles[0]

    def role_profile(self, profile_key: str | None = None) -> RoleProfileOut:
        self.seed_version()
        profile = self.active_profile_row(profile_key)
        targets = self.targets(profile_key=profile.profile_key)
        tier_counts = {tier: sum(1 for t in targets if t.tier == tier) for tier in v.TIERS}
        return RoleProfileOut(
            profile_key=profile.profile_key,
            name=profile.name,
            seniority=profile.seniority,
            config=dict(profile.config_json),
            tier_counts=tier_counts,
            required_skill_count=sum(1 for t in targets if t.required),
            critical_skills=[t.skill for t in targets if t.tier == "T1"],
        )

    def targets(self, *, profile_key: str | None = None, required: bool | None = None) -> list[SkillTarget]:
        self.seed_version()
        profile = self.active_profile_row(profile_key)
        required_tiers = _required_tiers(profile.config_json)
        out = [
            SkillTarget(
                skill=skill.skill_key,
                component=skill.component,
                tier=t.tier,
                importance=t.importance,
                target_score=t.target_score,
                floor_score=t.floor_score,
                required=required_tiers.get(t.tier, False),
            )
            for t, skill in self._repo.targets(profile.id)
        ]
        return [t for t in out if required is None or t.required == required]

    def target(self, skill_key: str, *, profile_key: str | None = None) -> SkillTarget:
        for t in self.targets(profile_key=profile_key):
            if t.skill == skill_key:
                return t
        raise _not_found(f"Target for skill {skill_key!r}")

    # ---------------------------------------------------------------------------------- roadmap
    def roadmap(self) -> RoadmapOut:
        self.seed_version()
        skills_of = self._repo.milestone_skill_keys()
        tracks: dict[str, list[MilestoneOut]] = {}
        for m in self._repo.milestones():
            tracks.setdefault(m.track, []).append(
                MilestoneOut(
                    key=m.milestone_key,
                    name=m.name,
                    position=m.position,
                    skills=skills_of.get(m.id, []),
                    extra_exit=list(m.extra_exit_json),
                    content=m.content,
                    starts_when=m.starts_when,
                )
            )
        items = [
            BaselineItemOut(
                key=b.item_key,
                position=b.position,
                name=b.name,
                minutes=b.minutes,
                observation_kind=b.observation_kind,
                covers=list(b.covers_json),
            )
            for b in self._repo.baseline_items()
        ]
        return RoadmapOut(
            tracks=[TrackOut(track=t, milestones=ms) for t, ms in tracks.items()],
            baseline_items=items,
            baseline_total_minutes=sum(i.minutes for i in items),
        )

    def milestone(self, milestone_key: str) -> MilestoneOut:
        for track in self.roadmap().tracks:
            for m in track.milestones:
                if m.key == milestone_key:
                    return m
        raise _not_found(f"Milestone {milestone_key!r}")

    # ---------------------------------------------------------------------------------- problems
    def _problem_out(self, problems: list[Problem]) -> list[ProblemOut]:
        mappings = self._repo.problem_skill_mappings([p.id for p in problems])
        return [
            ProblemOut(
                id=p.id,
                platform=p.platform,
                platform_key=p.platform_key,
                title=p.title,
                difficulty=p.difficulty,
                expected_minutes=p.expected_minutes,
                is_canonical=p.is_canonical,
                skills=[
                    ProblemSkillOut(skill=k, mapping_weight_bp=w, primary=w == v.PRIMARY_MAPPING_BP)
                    for k, w in mappings.get(p.id, [])
                ],
            )
            for p in problems
        ]

    def problems(self, *, skill: str | None = None, difficulty: str | None = None) -> list[ProblemOut]:
        self.seed_version()
        if difficulty is not None and difficulty not in v.DIFFICULTIES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown difficulty {difficulty!r}", 422)
        if skill is not None and self._repo.skill(skill) is None:
            raise _not_found(f"Skill {skill!r}")
        return self._problem_out(list(self._repo.problems(skill_key=skill, difficulty=difficulty)))

    def problem(self, problem_id: int) -> ProblemOut:
        self.seed_version()
        problem = self._repo.problem(problem_id)
        if problem is None or not problem.active:
            raise _not_found(f"Problem {problem_id}")
        return self._problem_out([problem])[0]

    def problem_by_key(self, platform: str, platform_key: str) -> ProblemOut:
        self.seed_version()
        problem = self._repo.problem_by_key(platform, platform_key)
        if problem is None or not problem.active:
            raise _not_found(f"Problem {platform}/{platform_key}")
        return self._problem_out([problem])[0]

    # ---------------------------------------------------------------------------------- templates
    def templates(
        self, *, component: str | None = None, stage: str | None = None, skill: str | None = None
    ) -> list[TemplateOut]:
        self.seed_version()
        rows = [t for t in self._repo.templates(component=component) if stage is None or stage in t.stages]
        if skill is not None:
            rows = [t for t in rows if t.applies_to and _applies(t.applies_to, skill)]
        return [_template_out(t) for t in rows]

    def resolve(
        self, *, component: str, stage: str, skill: str, gap_type: str | None = None
    ) -> TemplateResolutionOut:
        self.seed_version()
        if component not in v.TEMPLATE_COMPONENTS:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown component {component!r}", 422)
        if stage not in v.STAGES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown stage {stage!r}", 422)
        if gap_type is not None and gap_type not in v.GAP_TYPES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown gap type {gap_type!r}", 422)
        found = self._repo.skill(skill)
        if found is None:
            raise _not_found(f"Skill {skill!r}")
        rows = self._repo.templates()
        resolution = resolve_template(
            [_domain_template(t) for t in rows],
            component=component,
            stage=stage,
            skill_key=skill,
            gap_type=gap_type,
        )
        if resolution is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                f"No mission template resolves component={component} stage={stage} skill={skill}.",
                404,
                {"reason": "CONTENT_MISSING"},
            )
        row = next(t for t in rows if t.template_key == resolution.template.key)
        return TemplateResolutionOut(
            component=component,
            stage=stage,
            skill=skill,
            gap_type=gap_type,
            level=resolution.level,
            template=_template_out(row),
        )


def _required_tiers(config: Mapping[str, Any]) -> dict[str, bool]:
    tiers = config.get("tiers", {})
    return (
        {tier: bool(spec.get("required")) for tier, spec in tiers.items()}
        if isinstance(tiers, Mapping)
        else {}
    )


def _applies(applies_to: list[str], skill: str) -> bool:
    return any(skill.startswith(p) if p.endswith(".") else skill == p for p in applies_to)


def _template_out(t: MissionTemplate) -> TemplateOut:
    return TemplateOut(
        key=t.template_key,
        component=t.component,
        stages=list(t.stages),
        gap_types=t.gap_types,
        applies_to=t.applies_to,
        item_type=t.item_type,
        minutes=t.minutes,
        minutes_rule=t.minutes_rule,
        min_budget=t.min_budget,
        difficulty=t.difficulty,
        needs_problem=t.needs_problem,
        observation=dict(t.observation_json),
        pass_rule=t.pass_rule,
        partial_rule=t.partial_rule,
        output_level=t.output_level,
        next_on_pass=t.next_on_pass,
        next_on_fail=t.next_on_fail,
    )


def _domain_template(t: MissionTemplate) -> DomainTemplate:
    return DomainTemplate(
        key=t.template_key,
        component=t.component,
        stages=tuple(t.stages),
        gap_types=tuple(t.gap_types) if t.gap_types is not None else None,
        applies_to=tuple(t.applies_to) if t.applies_to is not None else None,
        item_type=t.item_type,
        minutes=t.minutes,
        minutes_rule=t.minutes_rule,
        min_budget=t.min_budget,
        difficulty=t.difficulty,
        needs_problem=t.needs_problem,
        observation=t.observation_json,
        pass_rule=t.pass_rule,
        partial_rule=t.partial_rule,
        output_level=t.output_level,
        next_on_pass=t.next_on_pass,
        next_on_fail=t.next_on_fail,
    )
