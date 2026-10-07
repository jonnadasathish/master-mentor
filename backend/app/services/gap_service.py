"""Gap read models over the latest mentor run (gap_states)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import cast

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.domain.communication.vocabulary import is_optional_communication_skill
from app.errors import AppError
from app.models import Evidence, GapState, Goal, MentorRun, RoleSkillTarget, Skill, SkillState
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.envelope import ErrorCode, Meta
from app.schemas.gaps import BlockedByOut, EvidenceRefOut, FocusOut, GapDetail, GapOut, GapReportOut
from app.services.skill_service import SkillService

STATUSES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "UNASSESSED", "BLOCKED", "PARKED")


class GapService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._skills = SkillService(session, clock)
        self._profiles = ProfileRepository(session)
        self._evidence = EvidenceRepository(session)
        self._states_cache: dict[int, SkillState] | None = None

    @property
    def _states(self) -> dict[int, SkillState]:
        if self._states_cache is None:
            self._states_cache = self._evidence.states()
        return self._states_cache

    def ensure_current_run(self) -> MentorRun:
        return self._skills.ensure_current_run()

    def meta(self, run: MentorRun, count: int | None = None) -> Meta:
        return self._skills.meta(run, count)

    def _profile_id(self) -> int | None:
        run = self._skills.latest_run()
        goal = self._s.get(Goal, run.goal_id) if run is not None and run.goal_id is not None else None
        profile = self._profiles.profile_row(goal.role_profile_id if goal else None)
        return profile.id if profile else None

    def _rows(self) -> list[tuple[GapState, Skill, RoleSkillTarget | None]]:
        stmt = (
            select(GapState, Skill, RoleSkillTarget)
            .join(Skill, Skill.id == GapState.skill_id)
            .outerjoin(
                RoleSkillTarget,
                and_(RoleSkillTarget.skill_id == Skill.id, RoleSkillTarget.profile_id == self._profile_id()),
            )
            .order_by(GapState.rank)
        )
        return [(g, s, t) for g, s, t in self._s.execute(stmt).all()]

    def _out(self, gap: GapState, skill: Skill, target: RoleSkillTarget | None) -> GapOut:
        state = self._states.get(skill.id)
        return GapOut(
            skill_key=skill.skill_key,
            name=skill.name,
            component=skill.component,
            tier=target.tier if target else None,
            current_score=state.score if state else None,
            effective_score=state.effective_score if state else None,
            level=state.level if state else None,
            confidence=state.confidence if state else "NONE",
            target_score=target.target_score if target else None,
            floor_score=target.floor_score if target else None,
            importance=target.importance if target else None,
            raw_gap=gap.raw_gap,
            severity=None if gap.severity is None else format(gap.severity, "f"),
            pressure_bp=gap.pressure_bp,
            priority=gap.priority,
            status=gap.status,
            rank=gap.rank,
            primary_gap_type=gap.primary_gap_type,
            gap_types=list(gap.gap_types_json),
            reason_codes=list(gap.reason_codes_json),
            blocked_by=[BlockedByOut.model_validate(b) for b in gap.blocked_by_json],
            parked_reason=gap.parked_reason,
            recommended_focus=FocusOut(stage=gap.focus_stage, focus_skill=gap.focus_skill),
            metrics=dict(gap.metrics_json),
        )

    def report(self, *, status: str | None, component: str | None, limit: int | None) -> GapReportOut:
        if status is not None and status not in STATUSES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown status {status!r}", 422)
        run = self._skills.latest_run()
        assert run is not None
        gaps = [
            self._out(g, s, t)
            for g, s, t in self._rows()
            if (status is None or g.status == status)
            and (
                component is None
                or (s.component == component and not is_optional_communication_skill(s.skill_key))
            )
        ]
        return GapReportOut(
            phase=run.phase.value if run.phase is not None else "BUILD",
            weeks_left=None
            if run.weeks_left is None
            else str(Decimal(run.weeks_left).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            infeasible_components=list(run.infeasible_components_json or []),
            calibration_mode=run.calibration_mode,
            gaps=gaps[:limit] if limit else gaps,
        )

    def detail(self, skill_key: str) -> GapDetail:
        for gap, skill, target in self._rows():
            if skill.skill_key == skill_key:
                base = self._out(gap, skill, target)
                evidence: dict[str, list[EvidenceRefOut]] = {}
                rows = {
                    (e.source_type, e.source_id): e
                    for e in self._s.scalars(
                        select(Evidence).where(
                            Evidence.skill_id == skill.id, Evidence.ruleset_version == gap.ruleset_version
                        )
                    )
                }
                for reason, refs in dict(gap.evidence_json).items():
                    out = []
                    for source_type, source_id in cast(list[list[object]], refs):
                        e = rows.get((str(source_type), int(str(source_id))))
                        out.append(
                            EvidenceRefOut(
                                source_type=str(source_type),
                                source_id=int(str(source_id)),
                                observed_on=e.observed_on if e else None,
                                level=e.level if e else None,
                                outcome_points=e.outcome_points if e else None,
                                source_key=e.source_key if e else None,
                            )
                        )
                    evidence[reason] = out
                return GapDetail(**base.model_dump(), evidence=evidence)
        raise AppError(ErrorCode.NOT_FOUND, f"Skill {skill_key!r} not found.", 404)
