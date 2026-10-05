"""Settings, versioned goals, and the engine view of the loaded catalog (SkillGraph + ProfileSpec)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.catalog.graph import validate_graph
from app.domain.profile.model import ProfileSpec, SkillGraph, SkillSpec, profile_from_config
from app.models import AppSettings, Goal, RoleProfile, RoleSkillTarget, Skill, SkillGroup
from app.repositories.catalog_repository import CatalogRepository


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    # ------------------------------------------------------------------ settings
    def settings(self) -> AppSettings | None:
        return self._s.get(AppSettings, 1)

    # ------------------------------------------------------------------ goals
    def goal_on(self, as_of: date) -> Goal | None:
        """The goal version valid on ``as_of`` (valid_from <= as_of < valid_to); latest id wins."""
        return self._s.scalar(
            select(Goal)
            .where(Goal.valid_from <= as_of, or_(Goal.valid_to.is_(None), Goal.valid_to > as_of))
            .order_by(Goal.id.desc())
            .limit(1)
        )

    def open_goals(self) -> Sequence[Goal]:
        return self._s.scalars(select(Goal).where(Goal.valid_to.is_(None)).order_by(Goal.id)).all()

    def goals(self) -> Sequence[Goal]:
        return self._s.scalars(select(Goal).order_by(Goal.valid_from, Goal.id)).all()

    def add_goal(self, goal: Goal) -> None:
        self._s.add(goal)
        self._s.flush()

    def overlapping(self, valid_from: date) -> Sequence[Goal]:
        return self._s.scalars(
            select(Goal).where(and_(Goal.valid_from > valid_from, Goal.valid_to.is_(None)))
        ).all()

    # ------------------------------------------------------------------ profiles
    def profile_row(self, profile_id: int | None) -> RoleProfile | None:
        if profile_id is not None:
            return self._s.get(RoleProfile, profile_id)
        profiles = CatalogRepository(self._s).profiles()
        return profiles[0] if len(profiles) == 1 else None

    def profile_by_key(self, profile_key: str) -> RoleProfile | None:
        return CatalogRepository(self._s).profile(profile_key)

    def engine_catalog(self, profile: RoleProfile) -> tuple[SkillGraph, ProfileSpec]:
        """Active skills (seed order) with this profile's targets, prerequisites and topological order."""
        spec = profile_from_config(profile.profile_key, profile.config_json)
        tiers = profile.config_json.get("tiers", {})
        required = {t: bool(v.get("required")) for t, v in tiers.items()} if isinstance(tiers, dict) else {}
        rows = self._s.execute(
            select(Skill, SkillGroup.group_key, RoleSkillTarget)
            .join(SkillGroup, Skill.group_id == SkillGroup.id)
            .join(
                RoleSkillTarget,
                and_(RoleSkillTarget.skill_id == Skill.id, RoleSkillTarget.profile_id == profile.id),
            )
            .where(Skill.active.is_(True))
            .order_by(Skill.position, Skill.id)
        ).all()
        keys = [skill.skill_key for skill, _, _ in rows]
        active = set(keys)
        edges: dict[str, list[tuple[str, int]]] = {k: [] for k in keys}
        for skill_key, prereq_key, min_score in CatalogRepository(self._s).prerequisite_edges():
            if skill_key in active and prereq_key in active:
                edges[skill_key].append((prereq_key, min_score))
        specs = [
            SkillSpec(
                key=skill.skill_key,
                component=skill.component,
                group=group_key,
                is_pattern=skill.is_pattern,
                tier=target.tier,
                importance=target.importance,
                target=target.target_score,
                floor=target.floor_score,
                required=required.get(target.tier, False),
                prerequisites=tuple(edges[skill.skill_key]),
            )
            for skill, group_key, target in rows
        ]
        report = validate_graph(keys, {k: [p for p, _ in v] for k, v in edges.items()})
        return SkillGraph.build(specs, report.topological_order), spec
