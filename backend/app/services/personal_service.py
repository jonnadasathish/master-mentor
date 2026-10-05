"""Personal roadmap and current state (D-080): read models over the engines' own output.

Everything is derived from ``MentorService.evaluate`` (read-only, deterministic for a given ``as_of``):
the gap report, skill states and the skill graph. The "what changed" comparison evaluates the previous
local day with the same engines. Self-reported context is shown beside observed values and never
influences them.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.baseline.calibration import calibration_phase
from app.domain.catalog.templates import resolve_template
from app.domain.clock import Clock
from app.domain.roadmap.personal import (
    BUILD,
    CONSOLIDATE,
    MAINTAIN,
    PARKED,
    SHARPEN,
    UNMEASURED,
    WHY_SIZE,
    PersonalRoadmap,
    RoadmapItem,
    build_personal_roadmap,
    roadmap_changes,
)
from app.domain.rulesets import get_ruleset
from app.errors import AppError
from app.models import MissionTemplate, Skill, SkillGroup
from app.schemas.envelope import ErrorCode
from app.schemas.starting import (
    BasedOnOut,
    ChangesOut,
    CurrentStateOut,
    FocusChangeOut,
    PersonalRoadmapOut,
    PrerequisiteOut,
    RoadmapItemOut,
    RoadmapSectionOut,
    SelfReportedGroupOut,
    SelfReportedSkillOut,
    StateSectionOut,
    WhyOut,
)
from app.services.catalog_service import _domain_template
from app.services.mentor_service import MentorService, RunResult
from app.services.starting_profile_service import StartingProfileService

SECTION_LIMIT = 8  # lists are capped; the section's own ``count`` is the total
CLAIM_LABELS = {
    "strengths": "STRONG",
    "weaknesses": "WEAK",
    "never_studied": "NEVER_STUDIED",
    "recently_studied": "RECENTLY_STUDIED",
}


class PersonalService:
    def __init__(self, session: Session, clock: Clock, ruleset_version: str) -> None:
        self._s = session
        self._mentor = MentorService(session, clock, ruleset_version=ruleset_version)
        self._profile = StartingProfileService(session, clock, ruleset_version)
        self._ruleset = get_ruleset(ruleset_version)
        self._names: dict[str, str] | None = None
        self._templates: list | None = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------ helpers
    def _skill_names(self) -> dict[str, str]:
        if self._names is None:
            self._names = {k: n for k, n in self._s.execute(select(Skill.skill_key, Skill.name)).all()}
        return self._names

    def _run(self, as_of_offset: int = 0) -> tuple[RunResult, PersonalRoadmap]:
        as_of = self._mentor.as_of_date() - timedelta(days=as_of_offset)
        result = self._mentor.evaluate(as_of)
        if result.outputs is None or result.outputs.gaps is None or result.context is None:
            raise AppError(ErrorCode.INVALID_STATE, "No catalog is loaded; run make seed.", 409)
        return result, build_personal_roadmap(result.outputs.gaps, result.states, result.context.graph)

    def _minutes(self, item: RoadmapItem) -> int | None:
        """Time of the next mission for this skill, from the mission library (None when it is rule-based)."""
        if item.focus_stage is None:
            return None
        if self._templates is None:
            self._templates = [_domain_template(t) for t in self._s.scalars(select(MissionTemplate))]
        focus = item.focus_skill or item.skill_key
        component = item.component if focus == item.skill_key else self._component_of(focus)
        found = resolve_template(
            self._templates,
            component=component,
            stage=item.focus_stage,
            skill_key=focus,
            gap_type=item.primary_gap_type,
        )
        return found.template.minutes if found else None

    def _component_of(self, skill_key: str) -> str:
        return str(self._s.scalar(select(Skill.component).where(Skill.skill_key == skill_key)) or "")

    def _item(self, item: RoadmapItem, *, with_minutes: bool = False) -> RoadmapItemOut:
        names = self._skill_names()
        return RoadmapItemOut(
            skill_key=item.skill_key,
            name=names.get(item.skill_key, item.skill_key),
            component=item.component,
            bucket=item.bucket,
            health=item.health,
            score=item.score,
            target=item.target,
            status=item.status,
            priority=item.priority,
            confidence=item.confidence,
            declared_unknown=item.declared_unknown,
            primary_gap_type=item.primary_gap_type,
            focus_stage=item.focus_stage,
            focus_skill=item.focus_skill,
            focus_skill_name=names.get(item.focus_skill) if item.focus_skill else None,
            reason_codes=list(item.reason_codes),
            importance=item.importance,
            prerequisites=[
                PrerequisiteOut(
                    skill=p.skill, name=names.get(p.skill, p.skill), score=p.score, min_score=p.min_score
                )
                for p in item.prerequisites
            ],
            next_step_minutes=self._minutes(item) if with_minutes else None,
        )

    def _section(self, items: tuple[RoadmapItem, ...], *, minutes: bool = False) -> RoadmapSectionOut:
        return RoadmapSectionOut(
            count=len(items), items=[self._item(i, with_minutes=minutes) for i in items[:SECTION_LIMIT]]
        )

    # ------------------------------------------------------------------ roadmap
    def roadmap(self) -> PersonalRoadmapOut:
        result, current = self._run()
        _, previous = self._run(1)
        context, outputs, calibration = result.context, result.outputs, result.calibration
        assert context is not None and outputs is not None and calibration is not None
        names = self._skill_names()
        profile = self._profile.get()
        gaps = outputs.gaps
        assert gaps is not None
        measured = sum(
            1
            for k, spec in context.graph.skills.items()
            if spec.required and result.states.get(k) is not None and result.states[k].assessed
        )
        required = sum(1 for spec in context.graph.skills.values() if spec.required)
        overdue = (
            sum(
                1
                for i in outputs.revision.items.values()
                if i.state == "ACTIVE" and i.due_date is not None and i.due_date < result.as_of_date
            )
            if outputs.revision
            else 0
        )
        weeks = gaps.weeks_left
        based_on = BasedOnOut(
            role=profile.target.role if profile.target else None,
            target_date=profile.target.target_date if profile.target else None,
            weeks_left=None if weeks is None else str(weeks.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            phase=gaps.phase,
            measured_skills=measured,
            required_skills=required,
            blocked_skills=sum(1 for g in gaps.gaps if g.status == "BLOCKED"),
            overdue_reviews=overdue,
        )
        changes = roadmap_changes(previous, current)

        def change_out(c) -> FocusChangeOut:  # type: ignore[no-untyped-def]
            return FocusChangeOut(
                skill_key=c.skill_key,
                name=names.get(c.skill_key, c.skill_key),
                priority_before=c.priority_before,
                priority_after=c.priority_after,
                reason_codes=list(c.reason_codes),
            )

        return PersonalRoadmapOut(
            as_of_date=result.as_of_date,
            calibration_phase=calibration_phase(calibration, self._ruleset),
            available=measured > 0 or any(i.bucket != UNMEASURED for i in current.items),
            based_on=based_on,
            focus_now=[self._item(i, with_minutes=True) for i in current.focus_now],
            sections={
                BUILD: self._section(current.bucket(BUILD), minutes=True),
                CONSOLIDATE: self._section(current.bucket(CONSOLIDATE), minutes=True),
                SHARPEN: self._section(current.bucket(SHARPEN), minutes=True),
                MAINTAIN: self._section(
                    tuple(sorted(current.bucket(MAINTAIN), key=lambda i: (-(i.score or 0), i.skill_key)))
                ),
                PARKED: self._section(current.bucket(PARKED)),
                UNMEASURED: self._section(current.bucket(UNMEASURED)),
                "later": self._section(current.later),
            },
            why=[
                WhyOut(
                    skill_key=i.skill_key,
                    name=names.get(i.skill_key, i.skill_key),
                    component=i.component,
                    score=i.score,
                    target=i.target,
                    importance=i.importance,
                    priority=i.priority,
                    reason_codes=list(i.reason_codes),
                    metrics={
                        k: (None if v is None else str(v) if isinstance(v, Decimal) else v)
                        for k, v in i.metrics.items()
                    },
                    prerequisites=[
                        PrerequisiteOut(
                            skill=p.skill,
                            name=names.get(p.skill, p.skill),
                            score=p.score,
                            min_score=p.min_score,
                        )
                        for p in i.prerequisites
                    ],
                )
                for i in current.focus_now[:WHY_SIZE]
            ],
            changes=ChangesOut(
                since=result.as_of_date - timedelta(days=1),
                changed=changes.changed,
                entered=[change_out(c) for c in changes.entered],
                left=[change_out(c) for c in changes.left],
            ),
        )

    # ------------------------------------------------------------------ current state
    def state(self) -> CurrentStateOut:
        result, current = self._run()
        assert result.context is not None and result.calibration is not None
        by_health = {
            h: tuple(i for i in current.items if i.health == h)
            for h in ("strong", "developing", "critical", "unknown")
        }
        strong = tuple(sorted(by_health["strong"], key=lambda i: (-(i.score or 0), i.skill_key)))
        profile = self._profile.get()
        groups = {
            k: (n, c)
            for k, n, c in self._s.execute(
                select(SkillGroup.group_key, SkillGroup.name, SkillGroup.component)
            ).all()
        }
        names = self._skill_names()
        by_skill = {i.skill_key: i for i in current.items}
        reported: dict[str, list[str]] = {}
        for claim, label in CLAIM_LABELS.items():
            for group in profile.self_report.get(claim, []):
                reported.setdefault(group, []).append(label)
        out: list[SelfReportedGroupOut] = []
        for group, claims in sorted(
            reported.items(), key=lambda kv: (groups.get(kv[0], (kv[0], ""))[1], kv[0])
        ):
            if group not in groups:
                continue
            members = [k for k, spec in result.context.graph.skills.items() if spec.group == group]
            skills = []
            for key in members:
                item = by_skill.get(key)
                state = result.states.get(key)
                if state is None or not state.assessed or item is None:
                    continue
                skills.append(
                    SelfReportedSkillOut(
                        skill_key=key,
                        name=names.get(key, key),
                        score=item.score,
                        target=item.target,
                        confidence=item.confidence,
                        status=item.status,
                        declared_unknown=item.declared_unknown,
                    )
                )
            out.append(
                SelfReportedGroupOut(
                    group_key=group,
                    name=groups[group][0],
                    component=groups[group][1],
                    claims=claims,
                    measured=sum(1 for s in skills if not s.declared_unknown),
                    total=len(members),
                    skills=skills,
                )
            )
        return CurrentStateOut(
            as_of_date=result.as_of_date,
            calibration_phase=calibration_phase(result.calibration, self._ruleset),
            counts={**current.health_counts, "total": len(current.items)},
            strong=self._section_state(strong),
            developing=self._section_state(by_health["developing"]),
            critical=self._section_state(by_health["critical"]),
            unknown=self._section_state(by_health["unknown"]),
            self_reported=out,
        )

    def _section_state(self, items: tuple[RoadmapItem, ...]) -> StateSectionOut:
        return StateSectionOut(count=len(items), items=[self._item(i) for i in items[:SECTION_LIMIT]])
