"""Read-only catalog queries. Every listing has an explicit ORDER BY (seed order or natural key)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    BaselineItem,
    CatalogLoad,
    MissionTemplate,
    Problem,
    ProblemSkill,
    RoadmapMilestone,
    RoadmapMilestoneSkill,
    RoleProfile,
    RoleSkillTarget,
    Skill,
    SkillGroup,
    SkillPrerequisite,
)


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    # --- version
    def current_load(self) -> CatalogLoad | None:
        return self._s.scalar(select(CatalogLoad).order_by(CatalogLoad.id.desc()).limit(1))

    def counts(self) -> dict[str, int]:
        def count(stmt: object) -> int:
            return int(self._s.scalar(stmt) or 0)  # type: ignore[call-overload]

        return {
            "skill_groups": count(select(func.count()).select_from(SkillGroup)),
            "skills": count(select(func.count()).select_from(Skill).where(Skill.active.is_(True))),
            "skill_prerequisites": count(select(func.count()).select_from(SkillPrerequisite)),
            "role_profiles": count(select(func.count()).select_from(RoleProfile)),
            "role_skill_targets": count(select(func.count()).select_from(RoleSkillTarget)),
            "problems": count(select(func.count()).select_from(Problem).where(Problem.active.is_(True))),
            "problem_skills": count(select(func.count()).select_from(ProblemSkill)),
            "mission_templates": count(select(func.count()).select_from(MissionTemplate)),
            "roadmap_milestones": count(select(func.count()).select_from(RoadmapMilestone)),
            "roadmap_milestone_skills": count(select(func.count()).select_from(RoadmapMilestoneSkill)),
            "baseline_items": count(select(func.count()).select_from(BaselineItem)),
        }

    # --- skills
    def groups(self) -> Sequence[SkillGroup]:
        return self._s.scalars(select(SkillGroup).order_by(SkillGroup.position)).all()

    def group(self, group_key: str) -> SkillGroup | None:
        return self._s.scalar(select(SkillGroup).where(SkillGroup.group_key == group_key))

    def skills(
        self, *, component: str | None = None, group_key: str | None = None, include_inactive: bool = False
    ) -> Sequence[tuple[Skill, str]]:
        stmt = select(Skill, SkillGroup.group_key).join(SkillGroup, Skill.group_id == SkillGroup.id)
        if not include_inactive:
            stmt = stmt.where(Skill.active.is_(True))
        if component is not None:
            stmt = stmt.where(Skill.component == component)
        if group_key is not None:
            stmt = stmt.where(SkillGroup.group_key == group_key)
        return [(row[0], row[1]) for row in self._s.execute(stmt.order_by(Skill.position)).all()]

    def skill(self, skill_key: str) -> tuple[Skill, str] | None:
        row = self._s.execute(
            select(Skill, SkillGroup.group_key)
            .join(SkillGroup, Skill.group_id == SkillGroup.id)
            .where(Skill.skill_key == skill_key)
        ).first()
        return (row[0], row[1]) if row else None

    def prerequisites(self, skill_id: int) -> Sequence[tuple[Skill, int]]:
        prereq = aliased(Skill)
        stmt = (
            select(prereq, SkillPrerequisite.min_score)
            .join(SkillPrerequisite, SkillPrerequisite.prereq_skill_id == prereq.id)
            .where(SkillPrerequisite.skill_id == skill_id)
            .order_by(SkillPrerequisite.position)
        )
        return [(row[0], row[1]) for row in self._s.execute(stmt).all()]

    def dependents(self, skill_id: int) -> Sequence[tuple[Skill, int]]:
        dependent = aliased(Skill)
        stmt = (
            select(dependent, SkillPrerequisite.min_score)
            .join(SkillPrerequisite, SkillPrerequisite.skill_id == dependent.id)
            .where(SkillPrerequisite.prereq_skill_id == skill_id, dependent.active.is_(True))
            .order_by(dependent.position)
        )
        return [(row[0], row[1]) for row in self._s.execute(stmt).all()]

    def prerequisite_edges(self) -> Sequence[tuple[str, str, int]]:
        """(skill_key, prereq_key, min_score) for every edge, in seed order."""
        skill, prereq = aliased(Skill), aliased(Skill)
        stmt = (
            select(skill.skill_key, prereq.skill_key, SkillPrerequisite.min_score)
            .join(SkillPrerequisite, SkillPrerequisite.skill_id == skill.id)
            .join(prereq, SkillPrerequisite.prereq_skill_id == prereq.id)
            .order_by(skill.position, SkillPrerequisite.position)
        )
        return [(row[0], row[1], row[2]) for row in self._s.execute(stmt).all()]

    # --- role profiles
    def profiles(self) -> Sequence[RoleProfile]:
        return self._s.scalars(select(RoleProfile).order_by(RoleProfile.profile_key)).all()

    def profile(self, profile_key: str) -> RoleProfile | None:
        return self._s.scalar(select(RoleProfile).where(RoleProfile.profile_key == profile_key))

    def targets(self, profile_id: int) -> Sequence[tuple[RoleSkillTarget, Skill]]:
        stmt = (
            select(RoleSkillTarget, Skill)
            .join(Skill, RoleSkillTarget.skill_id == Skill.id)
            .where(RoleSkillTarget.profile_id == profile_id)
            .order_by(Skill.position)
        )
        return [(row[0], row[1]) for row in self._s.execute(stmt).all()]

    def target(self, profile_id: int, skill_id: int) -> RoleSkillTarget | None:
        return self._s.get(RoleSkillTarget, (profile_id, skill_id))

    # --- roadmap
    def milestones(self) -> Sequence[RoadmapMilestone]:
        return self._s.scalars(
            select(RoadmapMilestone).order_by(RoadmapMilestone.track_position, RoadmapMilestone.position)
        ).all()

    def milestone(self, milestone_key: str) -> RoadmapMilestone | None:
        return self._s.scalar(select(RoadmapMilestone).where(RoadmapMilestone.milestone_key == milestone_key))

    def milestone_skill_keys(self) -> dict[int, list[str]]:
        stmt = (
            select(RoadmapMilestoneSkill.milestone_id, Skill.skill_key)
            .join(Skill, RoadmapMilestoneSkill.skill_id == Skill.id)
            .order_by(RoadmapMilestoneSkill.milestone_id, RoadmapMilestoneSkill.position)
        )
        out: dict[int, list[str]] = {}
        for milestone_id, key in self._s.execute(stmt).all():
            out.setdefault(milestone_id, []).append(key)
        return out

    def milestone_of_skill(self, skill_id: int) -> RoadmapMilestone | None:
        return self._s.scalar(
            select(RoadmapMilestone)
            .join(RoadmapMilestoneSkill, RoadmapMilestoneSkill.milestone_id == RoadmapMilestone.id)
            .where(RoadmapMilestoneSkill.skill_id == skill_id)
        )

    def baseline_items(self) -> Sequence[BaselineItem]:
        return self._s.scalars(select(BaselineItem).order_by(BaselineItem.position)).all()

    # --- problems
    def problems(self, *, skill_key: str | None = None, difficulty: str | None = None) -> Sequence[Problem]:
        stmt = select(Problem).where(Problem.active.is_(True))
        if difficulty is not None:
            stmt = stmt.where(Problem.difficulty == difficulty)
        if skill_key is not None:
            stmt = stmt.where(
                Problem.id.in_(
                    select(ProblemSkill.problem_id)
                    .join(Skill, ProblemSkill.skill_id == Skill.id)
                    .where(Skill.skill_key == skill_key)
                )
            )
        return self._s.scalars(stmt.order_by(Problem.id)).all()

    def problem(self, problem_id: int) -> Problem | None:
        return self._s.get(Problem, problem_id)

    def problem_by_key(self, platform: str, platform_key: str) -> Problem | None:
        return self._s.scalar(
            select(Problem).where(Problem.platform == platform, Problem.platform_key == platform_key)
        )

    def problem_skill_mappings(self, problem_ids: Sequence[int]) -> dict[int, list[tuple[str, int]]]:
        if not problem_ids:
            return {}
        stmt = (
            select(ProblemSkill.problem_id, Skill.skill_key, ProblemSkill.mapping_weight_bp)
            .join(Skill, ProblemSkill.skill_id == Skill.id)
            .where(ProblemSkill.problem_id.in_(problem_ids))
            .order_by(ProblemSkill.problem_id, ProblemSkill.mapping_weight_bp.desc(), Skill.skill_key)
        )
        out: dict[int, list[tuple[str, int]]] = {}
        for problem_id, key, weight in self._s.execute(stmt).all():
            out.setdefault(problem_id, []).append((key, weight))
        return out

    # --- mission templates
    def templates(self, *, component: str | None = None) -> Sequence[MissionTemplate]:
        stmt = select(MissionTemplate)
        if component is not None:
            stmt = stmt.where(MissionTemplate.component == component)
        return self._s.scalars(stmt.order_by(MissionTemplate.position)).all()
