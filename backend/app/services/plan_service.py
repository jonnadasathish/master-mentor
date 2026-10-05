"""Today page and frozen daily plans (MENTOR_ENGINE §2). Composition only: rules live in app.domain.mentor.

First ``GET /today`` of a local date = the plan-generating run: mentor run -> record backlog-triage /
auto-resume actions (if proposed) -> re-run -> generate -> persist frozen. Later runs never change the plan.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import replace as dc_replace
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.canonical import sha256_hex
from app.domain.catalog.model import Milestone
from app.domain.catalog.model import MissionTemplate as DomainTemplate
from app.domain.clock import Clock
from app.domain.mentor.model import (
    Blocker,
    CarriedItem,
    DailyPlan,
    ExitFacts,
    MockRoundInfo,
    PlanHistoryItem,
    PlanInputs,
    ProblemInfo,
    ReadinessView,
)
from app.domain.mentor.planner import generate_daily_plan
from app.domain.mentor.practice import PracticeObservation, summarize_practice, summarize_week
from app.domain.profile.goals import budget_for
from app.domain.review.weekly import week_bounds
from app.domain.revision.engine import backlog_minutes, revision_cap, triage_backlog
from app.domain.rulesets import get_ruleset
from app.errors import AppError
from app.models import (
    Assessment,
    AssessmentSkill,
    AuditLog,
    DailyPlanRow,
    MissionTemplate,
    PlanItemRow,
    Problem,
    ProblemSkill,
    ReadinessSnapshot,
    RevisionItemAction,
    RoadmapMilestone,
    RoadmapMilestoneSkill,
    Skill,
)
from app.models.system import MentorRunTrigger
from app.repositories.activity_repository import ActivityRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.activity import ProblemAttemptInput
from app.schemas.assessment import AssessmentInput
from app.schemas.envelope import ErrorCode
from app.schemas.mock import MockInput
from app.schemas.plan import (
    CalibrationOut,
    MessageOut,
    PlanItemOut,
    PlanOut,
    ProblemRefOut,
    ReadinessSummaryOut,
    TemplateOut,
    TodayOut,
    TopGapOut,
    WeekOut,
    WeekRevisionOut,
    WeekTrackOut,
)
from app.services.activity_service import ActivityService, _validation, problem_key
from app.services.assessment_service import AssessmentService
from app.services.mentor_service import MentorService, RunResult
from app.services.mock_service import MockService

DEFAULT_BUDGET = 90


def _naive(dt: datetime) -> datetime:
    return dt.astimezone(UTC).replace(tzinfo=None)


def readiness_view(result: RunResult) -> ReadinessView:
    """Readiness as the mentor consumes it (state, blockers, flags) from the same run's readiness engine."""
    r = result.outputs.readiness if result.outputs is not None else None
    if r is None:
        return ReadinessView()
    return ReadinessView(
        state=r.state,
        blockers=tuple(
            Blocker(
                gate=c.gate,
                message=c.message,
                component=c.subject if c.kind == "component" else None,
                skill=c.subject if c.kind == "skill" else None,
                actual=c.actual,
                required=c.required,
            )
            for c in r.blockers
        ),
        simulation_eligible=r.simulation_eligible,
        lapsed=r.lapsed,
        weighted_score=r.weighted_score,
    )


class PlanService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock
        self._mentor = MentorService(session, clock)
        self._plans = PlanRepository(session)
        self._profiles = ProfileRepository(session)
        self._ruleset = get_ruleset(self._mentor.ruleset_version)

    @property
    def mentor(self) -> MentorService:
        return self._mentor

    def practice_observations(self) -> list[PracticeObservation]:
        return self._practice_observations()

    def milestones(self) -> tuple[Milestone, ...]:
        return self._milestones()

    def exit_facts(self) -> ExitFacts:
        return self._exit_facts()

    # ------------------------------------------------------------------ inputs
    def _budget(self, day: date) -> tuple[int, int | None]:
        goal = self._profiles.goal_on(day)
        return (budget_for(goal.weekday_budgets_json, day), goal.id) if goal else (DEFAULT_BUDGET, None)

    def _templates(self) -> tuple[DomainTemplate, ...]:
        rows = self._s.scalars(select(MissionTemplate).order_by(MissionTemplate.template_key))
        return tuple(
            DomainTemplate(
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
            for t in rows
        )

    def _milestones(self) -> tuple[Milestone, ...]:
        skills: dict[int, list[str]] = {}
        for link, key in self._s.execute(
            select(RoadmapMilestoneSkill, Skill.skill_key)
            .join(Skill, Skill.id == RoadmapMilestoneSkill.skill_id)
            .order_by(RoadmapMilestoneSkill.milestone_id, RoadmapMilestoneSkill.position)
        ).all():
            skills.setdefault(link.milestone_id, []).append(key)
        return tuple(
            Milestone(
                m.milestone_key,
                m.track,
                m.track_position,
                m.position,
                m.name,
                tuple(skills.get(m.id, ())),
                tuple(m.extra_exit_json),
                m.content,
                m.starts_when,
            )
            for m in self._s.scalars(
                select(RoadmapMilestone).order_by(RoadmapMilestone.track_position, RoadmapMilestone.position)
            )
        )

    def _problems(self) -> tuple[ProblemInfo, ...]:
        mappings: dict[int, list[tuple[str, int]]] = {}
        for link, key in self._s.execute(
            select(ProblemSkill, Skill.skill_key)
            .join(Skill, Skill.id == ProblemSkill.skill_id)
            .order_by(ProblemSkill.problem_id, Skill.skill_key)
        ).all():
            mappings.setdefault(link.problem_id, []).append((key, link.mapping_weight_bp))
        stats = {
            s.problem.id: (s.attempt_count, s.last_attempt.attempted_on if s.last_attempt else None)
            for s in ActivityRepository(self._s).problems_with_stats()
        }
        return tuple(
            ProblemInfo(
                p.id,
                p.platform_key,
                p.difficulty,
                p.is_canonical,
                tuple(mappings.get(p.id, ())),
                *stats.get(p.id, (0, None)),
            )
            for p in self._s.scalars(select(Problem).where(Problem.active.is_(True)).order_by(Problem.id))
        )

    def _practice_observations(self) -> list[PracticeObservation]:
        out: list[PracticeObservation] = []
        attempts = ActivityRepository(self._s).attempts(ascending=True, limit=1_000_000)
        plan_minutes = self._plans.item_minutes(
            [a.attempt.plan_item_id for a in attempts if a.attempt.plan_item_id is not None]
        )
        mappings = {p.id: p.primary() for p in self._problems()}
        for a in attempts:
            primary = mappings.get(a.problem.id)
            out.append(
                PracticeObservation(
                    a.attempt.attempted_on,
                    (primary,) if primary else (),
                    a.attempt.time_seconds,
                    None,
                    plan_minutes.get(a.attempt.plan_item_id or -1),
                )
            )
        skills_by: dict[int, list[str]] = {}
        for link, key in self._s.execute(
            select(AssessmentSkill, Skill.skill_key).join(Skill, Skill.id == AssessmentSkill.skill_id)
        ).all():
            skills_by.setdefault(link.assessment_id, []).append(key)
        for s in self._s.scalars(select(Assessment)):
            out.append(
                PracticeObservation(
                    s.observed_on,
                    tuple(skills_by.get(s.id, ())),
                    s.time_seconds,
                    s.study_minutes,
                    None,
                    is_study=s.kind == "STUDY_SESSION",
                )
            )
        return out

    def _exit_facts(self) -> ExitFacts:
        def passes(kind: str, timed_only: bool) -> int:
            stmt = (
                select(Assessment.source_key)
                .join(AssessmentSkill, AssessmentSkill.assessment_id == Assessment.id)
                .where(Assessment.kind == kind, AssessmentSkill.outcome_points >= 70)
            )
            if timed_only:
                stmt = stmt.where(Assessment.timed.is_(True))
            return len(set(self._s.scalars(stmt)))

        return ExitFacts(
            machine_coding_passes=passes("MACHINE_CODING", False), timed_sd_passes=passes("SD_DESIGN", True)
        )

    def _history(self, as_of: date) -> tuple[PlanHistoryItem, ...]:
        return tuple(
            PlanHistoryItem(
                plan.plan_date, skill, item.stage, item.candidate_type, item.status, item.skip_reason
            )
            for item, plan, skill in self._plans.history(as_of)
        )

    def _carried(self, as_of: date) -> tuple[CarriedItem, ...]:
        yesterday = self._plans.plan_on(as_of - timedelta(days=1))
        if yesterday is None:
            return ()
        return tuple(
            CarriedItem(
                item.id,
                item.candidate_type,
                item.candidate_key,
                skill,
                item.stage,
                item.template_key,
                item.minutes,
                item.candidate_score,
                tuple(item.problem_ids_json),
                item.revision_item_key,
                item.battery_item_key,
                already_carried=item.carried_over_from_id is not None,
            )
            for item, skill in self._plans.items(yesterday.id)
            if item.status == "DEFERRED"
        )

    def _components_before(self, as_of: date, days: int) -> dict[str, int] | None:
        snap = self._s.get(ReadinessSnapshot, as_of - timedelta(days=days))
        if snap is None:
            return None
        return {str(c["key"]): int(str(c["score"])) for c in snap.components_json}

    def _triage_today(self, as_of: date) -> tuple[str, ...]:
        stmt = select(RevisionItemAction.item_key).where(
            RevisionItemAction.action_on == as_of,
            RevisionItemAction.action == "SUSPEND",
            RevisionItemAction.reason == "BACKLOG_TRIAGE",
        )
        return tuple(sorted(self._s.scalars(stmt)))

    # ------------------------------------------------------------------ generation
    def _run_with_triage(self, as_of: date, budget: int, *, allow_triage: bool) -> RunResult:
        result = self._mentor.recalculate(MentorRunTrigger.PLAN, as_of=as_of)
        out, ctx = result.outputs, result.context
        if not allow_triage or out is None or ctx is None or out.revision is None:
            return result
        proposals = triage_backlog(
            items=out.revision.items,
            graph=ctx.graph,
            parked=out.parked_skills(),
            daily_budget=budget,
            as_of_date=as_of,
            ruleset=self._ruleset,
        )
        if not proposals:
            return result
        now = _naive(self._clock.now_utc())
        for a in proposals:
            self._s.add(
                RevisionItemAction(
                    item_key=a.item_key,
                    action=a.action,
                    reason=a.reason,
                    action_on=as_of,
                    run_id=result.run_id,
                    created_at=now,
                )
            )
            self._s.add(
                AuditLog(
                    at=now,
                    entity_type="revision_item",
                    entity_id=a.item_key,
                    action=f"{a.action}_REVISION_ITEM",
                    payload_json={"reason": a.reason, "run_id": result.run_id},
                )
            )
        self._s.commit()
        return self._mentor.recalculate(MentorRunTrigger.PLAN, as_of=as_of)

    def _build(
        self, as_of: date, result: RunResult, budget: int, kept: Sequence[PlanItemRow] = ()
    ) -> tuple[DailyPlan, str]:
        out, ctx = result.outputs, result.context
        if (
            out is None
            or ctx is None
            or out.gaps is None
            or out.components is None
            or result.calibration is None
        ):
            raise AppError(ErrorCode.INVALID_STATE, "No catalog is loaded; run make seed.", 409)
        assert out.revision is not None and out.facts is not None
        done = [k for k in kept if k.status == "DONE"]
        skill_ids = {s.id: s.skill_key for s in self._s.scalars(select(Skill))}
        inputs = PlanInputs(
            as_of=as_of,
            budget=budget,
            phase=out.gaps.phase,
            weeks_left=out.gaps.weeks_left,
            target_date=ctx.goal.target_date if ctx.goal else None,
            goal_exists=ctx.goal is not None,
            calibration=result.calibration,
            gaps=out.gaps,
            states=out.states,
            facts=out.facts,
            components=out.components,
            graph=ctx.graph,
            profile=ctx.profile,
            revision=out.revision,
            templates=self._templates(),
            problems=self._problems(),
            milestones=self._milestones(),
            readiness=readiness_view(result),
            plan_history=self._history(as_of),
            practice=summarize_practice(self._practice_observations(), as_of, ctx.graph, ctx.profile),
            carried_over=self._carried(as_of),
            mock_rounds=tuple(MockRoundInfo(r.id, r.round_type, r.occurred_on) for r in ctx.readiness_rounds),
            exit_facts=dc_replace(
                self._exit_facts(),
                stories_per_skill=dict(ctx.stories_per_skill or {}),
                g6_passes=out.readiness is not None
                and any(g.gate == "G6" and g.passed for g in out.readiness.gates),
            ),
            triage_suspended_today=self._triage_today(as_of),
            component_scores_28d_ago=self._components_before(as_of, 28),
            done_minutes=sum(k.minutes for k in done),
            kept_items=max((k.position for k in kept), default=0),
            kept_skills=frozenset(
                skill_ids[k.skill_id]
                for k in kept
                if k.skill_id is not None and k.candidate_type != "REVISION"
            ),
            blocked_problem_ids=frozenset(p for k in kept for p in k.problem_ids_json),
            kept_keys=frozenset(k.candidate_key for k in kept),
        )
        plan = generate_daily_plan(inputs, self._ruleset)
        input_hash = sha256_hex(
            {
                "run_input_hash": result.input_hash,
                "budget": budget,
                "history": [asdict(h) for h in inputs.plan_history],
                "practice": asdict(inputs.practice),
                "carried": [asdict(c) for c in inputs.carried_over],
                "triage": list(inputs.triage_suspended_today),
                "kept": sorted(k.id for k in kept),
            }
        )
        return plan, input_hash

    def _persist_items(self, plan_id: int, plan: DailyPlan) -> None:
        ids = {s.skill_key: s.id for s in self._s.scalars(select(Skill))}
        for i in plan.items:
            self._s.add(
                PlanItemRow(
                    plan_id=plan_id,
                    position=i.position,
                    candidate_type=i.candidate_type,
                    candidate_key=i.candidate_key,
                    skill_id=ids.get(i.skill) if i.skill else None,
                    template_key=i.template_key,
                    stage=i.stage,
                    round_type=i.round_type,
                    problem_ids_json=list(i.problem_ids),
                    revision_item_key=i.revision_item_key,
                    battery_item_key=i.battery_item_key,
                    minutes=i.minutes,
                    candidate_score=i.score,
                    reason_codes_json=list(i.reason_codes),
                    explanation_json=asdict(i.explanation) if i.explanation else {},
                    status="PENDING",
                    no_evidence=False,
                    carried_over_from_id=i.carried_over_from_id,
                )
            )

    def _plan_fields(self, plan: DailyPlan) -> dict[str, Any]:
        return {
            "budget_minutes": plan.budget_minutes,
            "allocated_minutes": plan.allocated_minutes,
            "phase": plan.phase,
            "calibration_mode": plan.calibration_mode,
            "message_rule": plan.message.rule,
            "message_text": plan.message.text,
            "message_payload_json": _jsonable(dict(plan.message.payload)),
            "stop_list_json": [asdict(e) for e in plan.stop_list],
            "dropped_json": [asdict(d) for d in plan.dropped],
        }

    def ensure_today(self) -> DailyPlanRow:
        as_of = self._mentor.as_of_date()
        existing = self._plans.plan_on(as_of)
        if existing is not None:
            return existing
        budget, goal_id = self._budget(as_of)
        result = self._run_with_triage(as_of, budget, allow_triage=True)
        plan, input_hash = self._build(as_of, result, budget)
        row = DailyPlanRow(
            plan_date=as_of,
            run_id=result.run_id,
            goal_id=goal_id,
            input_hash=input_hash,
            regenerated_count=0,
            ruleset_version=result.ruleset_version,
            generated_at=_naive(self._clock.now_utc()),
            **self._plan_fields(plan),
        )
        self._s.add(row)
        self._s.flush()
        self._persist_items(row.id, plan)
        self._s.add(
            AuditLog(
                at=_naive(self._clock.now_utc()),
                entity_type="daily_plan",
                entity_id=str(row.id),
                action="GENERATE_PLAN",
                payload_json={"plan_date": as_of.isoformat(), "run_id": result.run_id},
            )
        )
        self._s.commit()
        return row

    def regenerate(self) -> DailyPlanRow:
        row = self.ensure_today()
        items = [i for i, _ in self._plans.items(row.id)]
        kept = [i for i in items if i.status in ("DONE", "SKIPPED")]
        now = _naive(self._clock.now_utc())
        for i in items:
            if i.status in ("PENDING", "DEFERRED"):
                i.status, i.status_changed_at = "DISCARDED", now
        self._s.flush()
        budget, _ = self._budget(row.plan_date)
        result = self._run_with_triage(row.plan_date, budget, allow_triage=False)
        plan, input_hash = self._build(row.plan_date, result, budget, kept)
        # positions of discarded items stay taken; new items follow the highest existing position
        offset = max((i.position for i in items), default=0) - max((k.position for k in kept), default=0)
        shifted = list(plan.items)
        for k, value in self._plan_fields(plan).items():
            setattr(row, k, value)
        row.run_id, row.input_hash = result.run_id, input_hash
        row.regenerated_count += 1
        self._persist_items(
            row.id,
            dc_replace(plan, items=tuple(dc_replace(i, position=i.position + offset) for i in shifted)),
        )
        self._s.add(
            AuditLog(
                at=now,
                entity_type="daily_plan",
                entity_id=str(row.id),
                action="REGENERATE_PLAN",
                payload_json={"kept": [k.id for k in kept], "regenerated_count": row.regenerated_count},
            )
        )
        self._s.commit()
        return row

    # ------------------------------------------------------------------ item actions
    def _pending(self, item_id: int) -> PlanItemRow:
        item = self._plans.item(item_id)
        if item is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Plan item {item_id} not found.", 404)
        if item.status != "PENDING":
            raise AppError(
                ErrorCode.INVALID_STATE, f"Plan item {item_id} is {item.status}, not PENDING.", 409
            )
        return item

    def _audit_item(self, item: PlanItemRow, action: str, payload: dict[str, Any]) -> None:
        self._s.add(
            AuditLog(
                at=_naive(self._clock.now_utc()),
                entity_type="plan_item",
                entity_id=str(item.id),
                action=action,
                payload_json=payload,
            )
        )

    def start(self, item_id: int) -> PlanItemRow:
        item = self._pending(item_id)
        item.started_at = _naive(self._clock.now_utc())
        self._s.commit()
        return item

    def skip(self, item_id: int, reason: str) -> PlanItemRow:
        item = self._pending(item_id)
        item.status, item.skip_reason, item.status_changed_at = (
            "SKIPPED",
            reason,
            _naive(self._clock.now_utc()),
        )
        self._audit_item(item, "SKIP_PLAN_ITEM", {"skip_reason": reason})
        self._s.commit()
        return item

    def defer(self, item_id: int) -> PlanItemRow:
        item = self._pending(item_id)
        item.status, item.status_changed_at = "DEFERRED", _naive(self._clock.now_utc())
        self._audit_item(item, "DEFER_PLAN_ITEM", {"carried_before": item.carried_over_from_id is not None})
        self._s.commit()
        return item

    def complete(
        self, item_id: int, observation: tuple[str, dict[str, Any]] | None, no_evidence: bool
    ) -> tuple[PlanItemRow, dict[str, Any] | None]:
        item = self._pending(item_id)
        if (observation is None) == (not no_evidence):
            raise _validation([("observation", "send an observation or no_evidence=true (exactly one)")])
        skill = self._s.get(Skill, item.skill_id) if item.skill_id else None
        recorded: dict[str, Any] | None = None
        links: dict[str, Any] = {}
        if item.revision_item_key:
            links |= {"revision_item_key": item.revision_item_key, "mode": "REVISION"}
        if item.battery_item_key:
            links |= {"battery_item_key": item.battery_item_key, "mode": "BASELINE"}
        try:
            if observation is not None:
                kind, body = observation
                if kind == "ATTEMPT":
                    attempt_body = {"problem_id": item.problem_ids_json[0]} if item.problem_ids_json else {}
                    payload = ProblemAttemptInput.model_validate({**attempt_body, **links, **body})
                    out = ActivityService(self._s, self._clock).record_attempt(payload, plan_item_id=item.id)
                    item.observation_type, item.observation_id = "ATTEMPT", out.id
                elif kind == "MOCK":
                    m_payload = MockInput.model_validate(body)
                    m_out = MockService(self._s, self._clock).record(m_payload, plan_item_id=item.id)
                    out = m_out  # type: ignore[assignment]
                    item.observation_type, item.observation_id = "MOCK", m_out.id
                else:
                    a_payload = AssessmentInput.model_validate({**links, **body})
                    a_out = AssessmentService(self._s, self._clock).record(a_payload, plan_item_id=item.id)
                    out = a_out  # type: ignore[assignment]
                    item.observation_type, item.observation_id = "ASSESSMENT", a_out.id
                recorded = out.model_dump(mode="json")
            elif skill is not None and item.candidate_type != "REVISION":
                study = AssessmentInput(
                    kind="STUDY_SESSION",
                    source_key=f"plan_item:{item.id}",
                    study_minutes=max(item.minutes, 1),
                    skills=[{"skill": skill.skill_key}],
                    battery_item_key=item.battery_item_key,
                )
                s_out = AssessmentService(self._s, self._clock).record(study, plan_item_id=item.id)
                item.observation_type, item.observation_id = "ASSESSMENT", s_out.id
                recorded = s_out.model_dump(mode="json")
        except ValidationError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Request validation failed.",
                422,
                {
                    "errors": [
                        {
                            "loc": ["body", "observation", *map(str, e["loc"])],
                            "msg": e["msg"],
                            "type": e["type"],
                        }
                        for e in exc.errors()
                    ]
                },
            ) from exc
        item = self._plans.item(item_id) or item
        self._mark_done(item, no_evidence)
        return item, recorded

    def open_battery_item(self, battery_item_key: str | None) -> PlanItemRow | None:
        """Today's pending plan item for this battery item, if today's plan exists (never creates one)."""
        if battery_item_key is None:
            return None
        plan = self._plans.plan_on(self._mentor.as_of_date())
        if plan is None:
            return None
        return next(
            (
                item
                for item, _ in self._plans.items(plan.id)
                if item.battery_item_key == battery_item_key and item.status == "PENDING"
            ),
            None,
        )

    def close_battery_item(
        self, item: PlanItemRow, observation_type: str, observation_id: int
    ) -> PlanItemRow:
        """A battery observation recorded outside the plan (e.g. the sweep) completes its plan item."""
        item = self._pending(item.id)
        item.observation_type, item.observation_id = observation_type, observation_id
        self._mark_done(item, no_evidence=False)
        return item

    def _mark_done(self, item: PlanItemRow, no_evidence: bool) -> None:
        item.status, item.no_evidence = "DONE", no_evidence
        now = _naive(self._clock.now_utc())
        item.completed_at = item.status_changed_at = now
        self._audit_item(
            item,
            "COMPLETE_PLAN_ITEM",
            {
                "observation_type": item.observation_type,
                "observation_id": item.observation_id,
                "no_evidence": no_evidence,
            },
        )
        self._s.commit()

    # ------------------------------------------------------------------ read models
    def item_out(self, item: PlanItemRow) -> PlanItemOut:
        template = self._s.scalar(
            select(MissionTemplate).where(MissionTemplate.template_key == item.template_key)
        )
        problems = (
            {p.id: p for p in self._s.scalars(select(Problem).where(Problem.id.in_(item.problem_ids_json)))}
            if item.problem_ids_json
            else {}
        )
        skill = self._s.get(Skill, item.skill_id) if item.skill_id else None
        return PlanItemOut(
            id=item.id,
            position=item.position,
            candidate_type=item.candidate_type,
            candidate_key=item.candidate_key,
            skill=skill.skill_key if skill else None,
            stage=item.stage,
            minutes=item.minutes,
            candidate_score=item.candidate_score,
            template=TemplateOut(
                key=template.template_key,
                observation=dict(template.observation_json),
                pass_rule=template.pass_rule,
                output_level=template.output_level,
                next_on_pass=template.next_on_pass,
            )
            if template
            else None,
            problems=[
                ProblemRefOut(id=p.id, key=problem_key(p), title=p.title, difficulty=p.difficulty, url=p.url)
                for pid in item.problem_ids_json
                if (p := problems.get(pid)) is not None
            ],
            revision_item_key=item.revision_item_key,
            battery_item_key=item.battery_item_key,
            round_type=item.round_type,
            reason_codes=list(item.reason_codes_json),
            explanation=dict(item.explanation_json),
            status=item.status,
            skip_reason=item.skip_reason,
            observation_type=item.observation_type,
            observation_id=item.observation_id,
            no_evidence=item.no_evidence,
            carried_over_from_id=item.carried_over_from_id,
            started_at=item.started_at.replace(tzinfo=UTC) if item.started_at else None,
            completed_at=item.completed_at.replace(tzinfo=UTC) if item.completed_at else None,
        )

    def plan_out(self, row: DailyPlanRow) -> PlanOut:
        items = [self.item_out(i) for i, _ in self._plans.items(row.id) if i.status != "DISCARDED"]
        done = sum(i.minutes for i in items if i.status == "DONE")
        return PlanOut(
            id=row.id,
            plan_date=row.plan_date,
            run_id=row.run_id,
            ruleset_version=row.ruleset_version,
            budget_minutes=row.budget_minutes,
            allocated_minutes=row.allocated_minutes,
            unallocated_minutes=row.budget_minutes - row.allocated_minutes,
            done_minutes=done,
            phase=row.phase,
            calibration_mode=row.calibration_mode,
            regenerated_count=row.regenerated_count,
            items=items,
            stop_list=list(row.stop_list_json),
            dropped=list(row.dropped_json),
            message=MessageOut(
                rule=row.message_rule, text=row.message_text, payload=dict(row.message_payload_json)
            ),
        )

    def plan_for(self, day: date) -> PlanOut:
        row = self._plans.plan_on(day)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND, f"No plan for {day.isoformat()}.", 404)
        return self.plan_out(row)

    def today(self) -> TodayOut:
        row = self.ensure_today()
        run_result = self._latest_outputs(row.plan_date)
        out, ctx, cal = run_result.outputs, run_result.context, run_result.calibration
        assert out is not None and out.gaps is not None and cal is not None and out.components is not None
        due = sum(
            1
            for i in (out.revision.items.values() if out.revision else ())
            if i.state == "ACTIVE" and i.due_date is not None and i.due_date == row.plan_date
        )
        overdue = sum(
            1
            for i in (out.revision.items.values() if out.revision else ())
            if i.state == "ACTIVE" and i.due_date is not None and i.due_date < row.plan_date
        )
        weeks = out.gaps.weeks_left
        view = readiness_view(run_result)
        return TodayOut(
            plan_date=row.plan_date,
            phase=out.gaps.phase,
            weeks_left=None if weeks is None else str(weeks.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            goal_exists=ctx is not None and ctx.goal is not None,
            calibration=CalibrationOut(
                active=cal.calibration_mode,
                assessed=cal.assessed_required,
                required=cal.required,
                assessed_pct=cal.assessed_pct,
                battery_done=cal.battery_done,
                battery_total=cal.battery_total,
                next_item=cal.next_item,
            ),
            readiness=ReadinessSummaryOut(
                state=view.state,
                weighted_score=out.components.weighted_score,
                limiting_component=out.components.limiting_component,
                blockers=[_jsonable(asdict(b)) for b in view.blockers[:3]],
            ),
            top_gaps=[
                TopGapOut(
                    skill_key=g.skill_key,
                    status=g.status,
                    priority=g.priority,
                    primary_gap_type=g.primary_gap_type,
                    focus_stage=g.focus_stage,
                    reason_codes=list(g.reason_codes),
                )
                for g in out.gaps.top_assessed(3)
            ],
            revisions={
                "due": due,
                "overdue": overdue,
                "backlog_minutes": backlog_minutes(
                    out.revision.items if out.revision else {},
                    out.parked_skills(),
                    row.plan_date,
                    self._ruleset,
                ),
                "cap_minutes": revision_cap(row.budget_minutes, self._ruleset),
            },
            plan=self.plan_out(row),
        )

    def week(self) -> WeekOut:
        """Week-to-date context (Monday..today): recorded practice by track, active days, revision plan items.
        Read-only: no mentor run, no plan row is created."""
        as_of = self._mentor.as_of_date()
        week_start, week_end = week_bounds(as_of)
        context, _ = self._mentor.context(as_of)
        goals = self._profiles.goals()
        first_goal = min((g.valid_from for g in goals), default=None)
        active = self._profiles.goal_on(as_of)
        summary = (
            summarize_week(self._practice_observations(), week_start, as_of, context.graph, context.profile)
            if context is not None
            else None
        )
        revision_items = [
            item
            for item, plan, _skill in self._plans.history(week_end + timedelta(days=1), days=7)
            if plan.plan_date >= week_start
            and item.candidate_type == "REVISION"
            and item.status != "DISCARDED"
        ]
        planned = len(revision_items)
        done = sum(1 for i in revision_items if i.status == "DONE")
        targets = context.profile.track_minutes if context is not None else {}
        return WeekOut(
            plan_date=as_of,
            week_start=week_start,
            week_end=week_end,
            preparation_day=None if first_goal is None else (as_of - first_goal).days + 1,
            target_minutes=sum(active.weekday_budgets_json) if active else None,
            practice_minutes=summary.total_minutes if summary else 0,
            active_days=summary.active_days if summary else 0,
            minutes_by_track=[
                WeekTrackOut(
                    track=t,
                    minutes=summary.track_minutes.get(t, 0) if summary else 0,
                    weekly_target=m,
                )
                for t, m in targets.items()
            ],
            revision=WeekRevisionOut(
                planned=planned, done=done, completion_pct=done * 100 // planned if planned else None
            ),
        )

    def _latest_outputs(self, as_of: date) -> RunResult:
        """Read-side evaluation for the Today header; writes nothing and never touches the plan."""
        return self._mentor.evaluate(as_of)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    return value
