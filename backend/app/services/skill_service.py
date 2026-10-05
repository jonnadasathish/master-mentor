"""Skill state read models + baseline/calibration status, composed over the catalog and the latest run.

Reads never calculate in the API layer: they ensure today's mentor run exists (a new local day re-runs the
engines with trigger PLAN, because recency weights depend on ``as_of_date``) and then read derived tables.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.baseline.calibration import CalibrationStatus
from app.domain.catalog.templates import resolve_template
from app.domain.clock import Clock
from app.domain.rulesets import get_ruleset
from app.errors import AppError
from app.models import GapState, MentorRun, MissionTemplate, RevisionItemRow, SkillState
from app.models.system import MentorRunTrigger
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.catalog import SkillSummary
from app.schemas.envelope import ErrorCode, Meta
from app.schemas.skills import (
    BaselineOut,
    BatteryItemOut,
    EvidenceOut,
    FocusPreview,
    GapSummary,
    PrerequisiteStatus,
    SkillDetail,
    SkillStateOut,
    SkillWithState,
)
from app.services.calibration_loader import load_calibration
from app.services.catalog_service import CatalogService, _domain_template
from app.services.mentor_service import MentorService

EVIDENCE_TIMELINE_LIMIT = 50
UNASSESSED = SkillStateOut(
    score=None,
    effective_score=None,
    level=None,
    confidence="NONE",
    label="UNASSESSED",
    peak_score=None,
    evidence_count=0,
    distinct_sources=0,
    last_practiced_on=None,
    last_observed_on=None,
    reality_capped=False,
    declared_unknown=False,
    assessed=False,
)


def _gap_out(row: GapState | None) -> GapSummary | None:
    if row is None:
        return None
    return GapSummary(
        status=row.status,
        priority=row.priority,
        rank=row.rank,
        primary_gap_type=row.primary_gap_type,
        focus_stage=row.focus_stage,
        focus_skill=row.focus_skill,
        reason_codes=list(row.reason_codes_json),
        blocked_by=list(row.blocked_by_json),
        parked_reason=row.parked_reason,
    )


def _state_out(row: SkillState | None) -> SkillStateOut:
    if row is None:
        return UNASSESSED
    return SkillStateOut(
        score=row.score,
        effective_score=row.effective_score,
        level=row.level,
        confidence=row.confidence,
        label=row.label,
        peak_score=row.peak_score,
        evidence_count=row.evidence_count,
        distinct_sources=row.distinct_sources,
        last_practiced_on=row.last_practiced_on,
        last_observed_on=row.last_observed_on,
        reality_capped=row.reality_capped,
        declared_unknown=row.declared_unknown,
        assessed=row.confidence != "NONE",
    )


class SkillService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._mentor = MentorService(session, clock)
        self._catalog = CatalogService(CatalogRepository(session))
        self._evidence = EvidenceRepository(session)

    @property
    def mentor(self) -> MentorService:
        return self._mentor

    # ------------------------------------------------------------------ run freshness
    def latest_run(self) -> MentorRun | None:
        return self._s.scalar(select(MentorRun).order_by(MentorRun.id.desc()).limit(1))

    def ensure_current_run(self) -> MentorRun:
        self._catalog.seed_version()  # 409 INVALID_STATE when no catalog is loaded
        run = self.latest_run()
        today = self._mentor.as_of_date()
        if run is None or run.as_of_date != today or run.ruleset_version != self._mentor.ruleset_version:
            self._mentor.recalculate(MentorRunTrigger.PLAN, as_of=today)
            run = self.latest_run()
        assert run is not None
        return run

    def meta(self, run: MentorRun, count: int | None = None) -> Meta:
        return Meta(
            as_of_date=run.as_of_date,
            ruleset_version=run.ruleset_version,
            seed_version=run.seed_version,
            run_id=run.id,
            count=count,
        )

    # ------------------------------------------------------------------ skills
    def _with_state(
        self, summary: SkillSummary, row: SkillState | None, gap: GapState | None = None
    ) -> SkillWithState:
        return SkillWithState(
            key=summary.key,
            name=summary.name,
            group=summary.group,
            component=summary.component,
            tier=summary.tier,
            importance=summary.importance,
            target_score=summary.target_score,
            floor_score=summary.floor_score,
            required=summary.required,
            state=_state_out(row),
            gap=_gap_out(gap),
        )

    def list_skills(
        self,
        *,
        component: str | None = None,
        group: str | None = None,
        tier: str | None = None,
        label: str | None = None,
    ) -> list[SkillWithState]:
        states = self._evidence.states()
        gaps = self._evidence.gaps()
        ids = self._skill_ids()
        out = [
            self._with_state(s, states.get(ids[s.key]), gaps.get(ids[s.key]))
            for s in self._catalog.skills(component=component, group=group, tier=tier)
        ]
        return [s for s in out if label is None or s.state.label == label]

    def detail(self, key: str) -> SkillDetail:
        found = CatalogRepository(self._s).skill(key)
        if found is None or not found[0].active:
            raise AppError(ErrorCode.NOT_FOUND, f"Skill {key!r} not found.", 404)
        skill = found[0]
        summary = next(s for s in self._catalog.skills(group=found[1]) if s.key == key)
        states = self._evidence.states()
        ids = self._skill_ids()
        row = states.get(skill.id)
        considered = {tuple(r) for r in (row.considered_evidence_json if row else [])}
        qualifying = {tuple(r) for r in (row.qualifying_evidence_json if row else [])}
        prerequisites = []
        for ref in self._catalog.prerequisites(key).prerequisites:
            pre = states.get(ids[ref.key])
            effective = pre.effective_score if pre else None
            prerequisites.append(
                PrerequisiteStatus(
                    skill=ref.key,
                    min_score=ref.min_score or 0,
                    effective_score=effective,
                    satisfied=effective is not None and effective >= (ref.min_score or 0),
                )
            )
        evidence = [
            EvidenceOut(
                source_type=e.source_type,
                source_id=e.source_id,
                rule=e.rule,
                kind=e.kind,
                level=e.level,
                outcome_points=e.outcome_points,
                is_scoring=e.is_scoring,
                observed_on=e.observed_on,
                observed_at=e.observed_at.replace(tzinfo=UTC),
                difficulty_bp=e.difficulty_bp,
                mapping_bp=e.mapping_bp,
                source_key=e.source_key,
                timed=e.timed,
                within_limit=e.within_limit,
                is_unseen=e.is_unseen,
                is_weakness=e.is_weakness,
                familiarity=e.familiarity,
                considered=(e.source_type, e.source_id, key) in considered,
                qualifying=(e.source_type, e.source_id, key) in qualifying,
            )
            for e in self._evidence.evidence_for_skill(
                skill.id, self._mentor.ruleset_version, EVIDENCE_TIMELINE_LIMIT
            )
        ]
        gap_row = self._evidence.gaps().get(skill.id)
        base = self._with_state(summary, row, gap_row)
        catalog_detail = self._catalog.skill(key)
        revision_items = [
            {
                "item_key": r.item_key,
                "item_type": r.item_type,
                "state": r.state,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "interval_index": r.interval_index,
                "lapses": r.lapses,
            }
            for r in self._s.scalars(
                select(RevisionItemRow)
                .where(RevisionItemRow.skill_id == skill.id)
                .order_by(RevisionItemRow.item_key)
            )
        ]
        focus = None
        if gap_row is not None and gap_row.focus_stage:
            templates = [_domain_template(t) for t in self._s.scalars(select(MissionTemplate))]
            focus_skill = gap_row.focus_skill or key
            focus_component = (
                skill.component
                if focus_skill == key
                else (CatalogRepository(self._s).skill(focus_skill) or (skill, ""))[0].component
            )
            resolution = resolve_template(
                templates,
                component=focus_component,
                stage=gap_row.focus_stage,
                skill_key=focus_skill,
                gap_type=gap_row.primary_gap_type,
            )
            t = resolution.template if resolution else None
            focus = FocusPreview(
                stage=gap_row.focus_stage,
                template_key=t.key if t else None,
                minutes=t.minutes if t else None,
                pass_rule=t.pass_rule if t else None,
                observation_kind=str(t.observation.get("kind")) if t else None,
            )
        return SkillDetail(
            **base.model_dump(),
            prerequisites=prerequisites,
            dependents=[d.key for d in catalog_detail.dependents],
            milestone=(
                {
                    "key": catalog_detail.milestone.key,
                    "name": catalog_detail.milestone.name,
                    "track": catalog_detail.milestone.track,
                }
                if catalog_detail.milestone
                else None
            ),
            revision_items=revision_items,
            focus=focus,
            evidence=evidence,
        )

    def _skill_ids(self) -> dict[str, int]:
        return {s.skill_key: s.id for s, _ in CatalogRepository(self._s).skills(include_inactive=True)}

    # ------------------------------------------------------------------ baseline
    def calibration(self) -> CalibrationStatus:
        context, _ = self._mentor.context(self._mentor.as_of_date())
        if context is None:
            raise AppError(ErrorCode.INVALID_STATE, "No catalog is loaded; run make seed.", 409)
        ids = self._skill_ids()
        rows = self._evidence.states()
        assessed = {
            k for k in context.graph.skills if (r := rows.get(ids[k])) is not None and r.confidence != "NONE"
        }
        return load_calibration(self._s, context.graph, assessed, get_ruleset(self._mentor.ruleset_version))

    def baseline(self) -> BaselineOut:
        status = self.calibration()
        return BaselineOut(
            items=[
                BatteryItemOut(
                    key=i.key,
                    position=i.position,
                    name=i.name,
                    minutes=i.minutes,
                    observation_kind=i.observation_kind,
                    covers=list(i.covers),
                    complete=i.complete,
                )
                for i in status.items
            ],
            battery_complete=status.battery_complete,
            battery_done=status.battery_done,
            battery_total=status.battery_total,
            next_item=status.next_item,
            required=status.required,
            assessed_required=status.assessed_required,
            assessed_pct=status.assessed_pct,
            calibration_mode=status.calibration_mode,
        )
