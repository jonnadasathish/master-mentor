"""Mentor run orchestration (D-031 order): raw observations -> evidence -> skill states -> components -> gaps,
persisted with a mentor_runs row.

The calculation itself is pure (``app.domain``, see ``compute``); this service only loads inputs, calls
the engines with an explicit ``as_of_date`` + ruleset, and rewrites the derived tables. Same inputs ->
same rows and same ``input_hash``, independent of wall-clock time and input order.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.baseline.calibration import CalibrationStatus
from app.domain.clock import Clock, local_date
from app.domain.evidence.derive import derive_evidence
from app.domain.evidence.model import EvidenceRow
from app.domain.gaps.engine import calculate_gaps
from app.domain.gaps.facts import MockRoundSummary, build_all_facts, mock_weakness_skills
from app.domain.gaps.model import Gap, GapReport, RevisionFacts, SkillFacts
from app.domain.mentor_run import build_run_identity
from app.domain.profile.model import Goal, ProfileSpec, SkillGraph
from app.domain.readiness.components import ComponentScores, calculate_component_scores
from app.domain.readiness.engine import (
    FinalSimulation,
    MockRound,
    Readiness,
    calculate_readiness,
    recent_passing_components,
)
from app.domain.revision.engine import (
    StoryFact,
    WeaknessRound,
    mock_weakness_items,
    project_revision_items,
    revision_facts,
    revision_health,
    story_items,
)
from app.domain.revision.inputs import revision_observations
from app.domain.revision.model import RevisionAction, RevisionItem, RevisionProjection
from app.domain.rulesets import get_ruleset
from app.domain.skills.state import SkillState, calculate_skill_states
from app.models import (
    Evidence,
    GapState,
    MentorRun,
    ReadinessSnapshot,
    RevisionItemRow,
    SkillDailySnapshot,
)
from app.models import SkillState as SkillStateRow
from app.models.system import MentorRunTrigger, PrepPhase
from app.repositories.activity_repository import ActivityRepository
from app.repositories.evidence_repository import EngineInputs, EvidenceRepository, StoredGap, StoredState
from app.repositories.profile_repository import ProfileRepository
from app.repositories.system_repository import SystemRepository
from app.services.calibration_loader import load_calibration

FALLBACK_TIMEZONE = "UTC"


@dataclass(frozen=True)
class SkillDelta:
    skill_key: str
    before: StoredState | None
    after: StoredState

    def as_json(self) -> dict[str, object]:
        def side(s: StoredState | None) -> dict[str, object] | None:
            if s is None:
                return None
            return {"score": s.score, "effective": s.effective, "level": s.level, "confidence": s.confidence}

        return {"skill_key": self.skill_key, "before": side(self.before), "after": side(self.after)}


@dataclass(frozen=True)
class GapDelta:
    skill_key: str
    before: StoredGap | None
    after: StoredGap

    def as_json(self) -> dict[str, object]:
        def side(g: StoredGap | None) -> dict[str, object] | None:
            return None if g is None else {"priority": g.priority, "status": g.status}

        return {"skill_key": self.skill_key, "before": side(self.before), "after": side(self.after)}


@dataclass(frozen=True)
class EngineContext:
    """Catalog + goal inputs of a run (everything besides observations)."""

    graph: SkillGraph
    profile: ProfileSpec
    goal: Goal | None
    mock_rounds: tuple[MockRoundSummary, ...] = ()
    revision_actions: tuple[RevisionAction, ...] = ()
    readiness_rounds: tuple[MockRound, ...] = ()  # mock interview rounds (Slice 10)
    final_simulations: tuple[FinalSimulation, ...] = ()
    previous_states: Mapping[date, str] | None = None  # readiness snapshot states before as_of
    extra_revision_items: tuple[RevisionItem, ...] = ()  # MOCK_WEAKNESS + STORY items (created outside rows)
    stories_per_skill: Mapping[str, int] | None = None


@dataclass(frozen=True)
class Outputs:
    rows: list[EvidenceRow]
    states: dict[str, SkillState]
    components: ComponentScores | None
    gaps: GapReport | None
    revision: RevisionProjection | None = None
    facts: Mapping[str, SkillFacts] | None = None
    readiness: Readiness | None = None

    def parked_skills(self) -> set[str]:
        return {g.skill_key for g in self.gaps.gaps if g.status == "PARKED"} if self.gaps else set()


@dataclass(frozen=True)
class RunResult:
    run_id: int
    as_of_date: date
    ruleset_version: str
    seed_version: str
    input_hash: str
    evidence_rows: int
    states: dict[str, SkillState]
    skill_deltas: list[SkillDelta]
    gap_report: GapReport | None = None
    gap_deltas: tuple[GapDelta, ...] = ()
    calibration: CalibrationStatus | None = None
    outputs: Outputs | None = None
    context: EngineContext | None = None
    revision_changes: tuple[dict[str, object], ...] = ()
    readiness_change: dict[str, object] | None = None

    def effects(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "skill_deltas": [d.as_json() for d in self.skill_deltas],
            "gap_deltas": [d.as_json() for d in self.gap_deltas],
            "revision_changes": list(self.revision_changes),
            "readiness_change": self.readiness_change,
        }


def inputs_fingerprint_payload(
    inputs: EngineInputs, context: EngineContext | None = None
) -> dict[str, object]:
    """Order-independent canonical payload of every engine input (hashed into mentor_runs.input_hash)."""
    payload: dict[str, object] = {
        "skills": sorted([s.key, s.component, s.is_pattern] for s in inputs.skills.values()),
        "attempts": sorted((asdict(a) for a in inputs.attempts), key=lambda a: int(str(a["id"]))),
        "assessments": sorted((asdict(a) for a in inputs.assessments), key=lambda a: int(str(a["id"]))),
        "mock_rounds": sorted((asdict(m) for m in inputs.mock_rounds), key=lambda m: int(str(m["id"]))),
    }
    if context is not None:
        payload["profile"] = context.profile.profile_key
        payload["goal"] = None if context.goal is None else asdict(context.goal)
        payload["previous_readiness"] = sorted(
            [d.isoformat(), st] for d, st in (context.previous_states or {}).items()
        )
        payload["mock_rounds_ctx"] = [asdict(r) for r in context.readiness_rounds]
        payload["extra_revision_items"] = sorted(i.item_key for i in context.extra_revision_items)
        payload["revision_actions"] = [
            asdict(a) for a in sorted(context.revision_actions, key=lambda a: a.id)
        ]
        payload["targets"] = sorted(
            [s.key, s.tier, s.importance, s.target, s.floor, list(s.prerequisites)]
            for s in context.graph.skills.values()
        )
    return payload


def compute(
    inputs: EngineInputs, as_of: date, ruleset_version: str, context: EngineContext | None = None
) -> Outputs:
    """The pure part of a mentor run (also used by the replay/determinism tests)."""
    ruleset = get_ruleset(ruleset_version)
    rows = derive_evidence(
        attempts=inputs.attempts,
        assessments=inputs.assessments,
        mock_rounds=inputs.mock_rounds,
        skills=inputs.skills,
        ruleset=ruleset,
    )
    states = calculate_skill_states(list(inputs.skills), rows, as_of, ruleset)
    if context is None:
        return Outputs(rows, states, None, None)
    components = calculate_component_scores(states, context.graph, context.profile)
    revision = project_revision_items(
        observations=revision_observations(inputs.attempts, inputs.assessments, rows),
        actions=context.revision_actions,
        graph=context.graph,
        as_of_date=as_of,
        ruleset=ruleset,
        extra_items=context.extra_revision_items,
    )
    rev_facts = {
        skill: RevisionFacts(max_active_lapses=lapses, has_overdue_item=overdue, has_leech=leech)
        for skill, (lapses, overdue, leech) in revision_facts(revision, as_of).items()
    }
    weak = mock_weakness_skills(context.mock_rounds, as_of, ruleset)
    facts = build_all_facts(list(context.graph.skills), rows, as_of, ruleset, weak)
    report = calculate_gaps(
        skill_states=states,
        component_scores=components,
        profile=context.profile,
        graph=context.graph,
        skill_facts=facts,
        revision_facts=rev_facts,
        goal=context.goal,
        as_of_date=as_of,
        ruleset=ruleset,
    )
    parked = {g.skill_key for g in report.gaps if g.status == "PARKED"}
    readiness = calculate_readiness(
        components=components,
        states=states,
        gap_report=report,
        graph=context.graph,
        profile=context.profile,
        mock_rounds=context.readiness_rounds,
        final_simulations=context.final_simulations,
        revision_health=revision_health(revision, context.graph, parked, as_of, ruleset),
        recent_components=recent_passing_components(
            rows, context.graph, as_of, int(str(context.profile.gate_parameters.get("G8_recency_days", 21)))
        ),
        previous_states=context.previous_states or {},
        as_of_date=as_of,
    )
    return Outputs(rows, states, components, report, revision, facts, readiness)


class MentorService:
    def __init__(self, session: Session, clock: Clock, *, ruleset_version: str | None = None) -> None:
        self._s = session
        self._clock = clock
        self._repo = EvidenceRepository(session)
        self._profiles = ProfileRepository(session)
        self._ruleset_version = ruleset_version or get_settings().ruleset_version

    @property
    def ruleset_version(self) -> str:
        return self._ruleset_version

    def as_of_date(self) -> date:
        tz = ActivityRepository(self._s).timezone() or FALLBACK_TIMEZONE
        return local_date(self._clock.now_utc(), tz)

    def context(self, as_of: date) -> tuple[EngineContext | None, int | None]:
        """Catalog + goal valid on ``as_of``; None when no catalog/profile is loaded."""
        goal_row = self._profiles.goal_on(as_of)
        profile_row = self._profiles.profile_row(goal_row.role_profile_id if goal_row else None)
        if profile_row is None:
            return None, None
        graph, profile = self._profiles.engine_catalog(profile_row)
        if not graph.skills:
            return None, None
        goal = (
            Goal(goal_row.id, goal_row.target_date, tuple(goal_row.weekday_budgets_json))
            if goal_row
            else None
        )
        ruleset = get_ruleset(self._ruleset_version)
        facts = self._repo.mock_facts()
        weakness_rounds = [
            WeaknessRound(f.round_id, f.occurred_on, tuple((k, p) for k, p, w in f.skills if w))
            for f in facts
        ]
        stories = self._repo.story_facts()
        per_skill: dict[str, int] = {}
        for _, _, _, competencies in stories:
            for key in competencies:
                per_skill[key] = per_skill.get(key, 0) + 1
        readiness_rounds = tuple(
            MockRound(
                f.round_id,
                f.mock_id,
                f.occurred_on,
                f.round_type,
                f.source,
                f.round_score,
                order=int(f.occurred_at.timestamp()) * 100 + f.position,
            )
            for f in facts
        )
        finals: dict[int, list[MockRound]] = {}
        for f, r in zip(facts, readiness_rounds, strict=True):
            if f.is_final_simulation:
                finals.setdefault(f.mock_id, []).append(r)
        context = EngineContext(
            graph=graph,
            profile=profile,
            goal=goal,
            mock_rounds=tuple(
                MockRoundSummary(w.round_id, w.occurred_on, tuple(k for k, _ in w.weaknesses))
                for w in weakness_rounds
            ),
            revision_actions=tuple(self._repo.revision_actions()),
            readiness_rounds=readiness_rounds,
            final_simulations=tuple(
                FinalSimulation(mock_id, rounds[0].occurred_on, rounds[0].source, tuple(rounds))
                for mock_id, rounds in finals.items()
            ),
            previous_states=self._repo.previous_readiness_states(as_of),
            extra_revision_items=tuple(
                [
                    *mock_weakness_items(weakness_rounds, ruleset),
                    *story_items([StoryFact(i, d, first) for i, d, first, _ in stories], ruleset),
                ]
            ),
            stories_per_skill=per_skill,
        )
        return context, goal_row.id if goal_row else None

    def recalculate(self, trigger: MentorRunTrigger, *, as_of: date | None = None) -> RunResult:
        """One synchronous mentor run. Commits; derived tables are replaced atomically."""
        started = time.perf_counter_ns()
        as_of_date = as_of or self.as_of_date()
        seed_version = SystemRepository(self._s).loaded_seed_version() or "none"
        inputs = self._repo.engine_inputs()
        context, goal_id = self.context(as_of_date)
        identity = build_run_identity(
            as_of_date=as_of_date,
            ruleset_version=self._ruleset_version,
            seed_version=seed_version,
            inputs=inputs_fingerprint_payload(inputs, context),
        )
        out = compute(inputs, as_of_date, self._ruleset_version, context)
        ruleset = get_ruleset(self._ruleset_version)
        calibration = (
            load_calibration(
                self._s, context.graph, {k for k, s in out.states.items() if s.assessed}, ruleset
            )
            if context is not None
            else None
        )

        previous_states = self._repo.stored_states()
        previous_gaps = self._repo.stored_gaps()
        previous_items = self._repo.stored_revision_items()
        previous_snapshot = self._repo.readiness_snapshot(as_of_date)
        previous_readiness = (
            (previous_snapshot.state, [str(b["message"]) for b in previous_snapshot.blockers_json])
            if previous_snapshot is not None
            else None
        )
        report = out.gaps
        run = MentorRun(
            run_at=self._clock.now_utc().astimezone(UTC).replace(tzinfo=None),
            as_of_date=as_of_date,
            trigger=trigger,
            goal_id=goal_id,
            ruleset_version=self._ruleset_version,
            seed_version=seed_version,
            input_hash=identity.input_hash,
            phase=PrepPhase(report.phase) if report is not None and goal_id is not None else None,
            weeks_left=report.weeks_left if report is not None and goal_id is not None else None,
            calibration_mode=calibration.calibration_mode if calibration is not None and goal_id else None,
            infeasible_components_json=list(report.infeasible_components) if report is not None else None,
        )
        self._s.add(run)
        self._s.flush()
        gaps: dict[str, Gap] = report.by_skill() if report is not None else {}
        self._repo.replace_evidence(out.rows, inputs.skill_ids, self._ruleset_version)
        self._repo.replace_states(
            out.states,
            inputs.skill_ids,
            run_id=run.id,
            as_of=as_of_date,
            ruleset_version=self._ruleset_version,
            gaps=gaps,
        )
        self._repo.replace_gaps(
            gaps,
            inputs.skill_ids,
            run_id=run.id,
            goal_id=goal_id,
            as_of=as_of_date,
            ruleset_version=self._ruleset_version,
        )
        if out.revision is not None:
            self._repo.replace_revision_items(out.revision.items, inputs.skill_ids, run_id=run.id)
        if out.readiness is not None:
            self._repo.replace_readiness_snapshot(
                out.readiness, run_id=run.id, ruleset_version=self._ruleset_version
            )
        run.duration_ms = (time.perf_counter_ns() - started) // 1_000_000
        self._s.commit()

        skill_deltas: list[SkillDelta] = []
        for key, st in out.states.items():
            after = StoredState(st.score, st.effective_score, st.level, st.confidence)
            before = previous_states.get(inputs.skill_ids[key])
            if before != after and not (before is None and st.confidence == "NONE"):
                skill_deltas.append(SkillDelta(key, before, after))
        gap_deltas = []
        for key, g in gaps.items():
            after_gap = StoredGap(g.priority, g.status)
            before_gap = previous_gaps.get(inputs.skill_ids[key]) if key in inputs.skill_ids else None
            if before_gap is not None and before_gap != after_gap:
                gap_deltas.append(GapDelta(key, before_gap, after_gap))
        revision_changes: list[dict[str, object]] = []
        for key, item in (out.revision.items if out.revision else {}).items():
            item_before = previous_items.get(key)
            due_iso = item.due_date.isoformat() if item.due_date else None
            if item_before is None:
                revision_changes.append({"item_key": key, "change": "CREATED", "due_date": due_iso})
            elif item_before != (item.state, due_iso, item.interval_index):
                revision_changes.append(
                    {"item_key": key, "change": "UPDATED", "state": item.state, "due_date": due_iso}
                )
        readiness_change: dict[str, object] | None = None
        if out.readiness is not None:
            after_blockers = [c.message for c in out.readiness.blockers]
            before_state, before_blockers = previous_readiness or (None, [])
            readiness_change = {
                "before": before_state,
                "after": out.readiness.state,
                "blockers_added": [b for b in after_blockers if b not in before_blockers],
                "blockers_removed": [b for b in before_blockers if b not in after_blockers],
            }
        return RunResult(
            run_id=run.id,
            as_of_date=as_of_date,
            ruleset_version=self._ruleset_version,
            seed_version=seed_version,
            input_hash=identity.input_hash,
            evidence_rows=len(out.rows),
            states=out.states,
            skill_deltas=skill_deltas,
            readiness_change=readiness_change,
            gap_report=report,
            gap_deltas=tuple(gap_deltas),
            calibration=calibration,
            outputs=out,
            context=context,
            revision_changes=tuple(revision_changes),
        )

    def evaluate(self, as_of: date) -> RunResult:
        """Same pure computation as a run, without writing anything (read models: Today header, readiness).

        ``run_id`` is the latest persisted run; outputs are recomputed so they always match ``as_of``.
        """
        seed_version = SystemRepository(self._s).loaded_seed_version() or "none"
        inputs = self._repo.engine_inputs()
        context, _ = self.context(as_of)
        identity = build_run_identity(
            as_of_date=as_of,
            ruleset_version=self._ruleset_version,
            seed_version=seed_version,
            inputs=inputs_fingerprint_payload(inputs, context),
        )
        out = compute(inputs, as_of, self._ruleset_version, context)
        ruleset = get_ruleset(self._ruleset_version)
        calibration = (
            load_calibration(
                self._s, context.graph, {k for k, s in out.states.items() if s.assessed}, ruleset
            )
            if context is not None
            else None
        )
        latest = self._s.scalar(select(MentorRun.id).order_by(MentorRun.id.desc()).limit(1)) or 0
        return RunResult(
            run_id=int(latest),
            as_of_date=as_of,
            ruleset_version=self._ruleset_version,
            seed_version=seed_version,
            input_hash=identity.input_hash,
            evidence_rows=len(out.rows),
            states=out.states,
            skill_deltas=[],
            gap_report=out.gaps,
            calibration=calibration,
            outputs=out,
            context=context,
        )

    def rebuild(self) -> dict[str, int]:
        """Truncate derived tables and replay from raw observations (API_SPEC POST /admin/rebuild).

        Every snapshot date that existed is recomputed "as of" that date (rows observed later are ignored by
        the state calculation), then today's run is recomputed. Raw tables are never touched.
        """
        started = time.perf_counter_ns()
        dates = sorted(set(self._s.scalars(select(SkillDailySnapshot.snapshot_date).distinct())))
        self._s.execute(delete(SkillDailySnapshot))
        self._s.execute(delete(GapState))
        self._s.execute(delete(RevisionItemRow))
        self._s.execute(delete(ReadinessSnapshot))
        self._s.execute(delete(SkillStateRow))
        self._s.execute(delete(Evidence))
        self._s.commit()
        today = self.as_of_date()
        runs = 0
        for day in [d for d in dates if d < today]:
            self.recalculate(MentorRunTrigger.REBUILD, as_of=day)
            runs += 1
        result = self.recalculate(MentorRunTrigger.REBUILD, as_of=today)
        runs += 1
        snapshots = len(set(self._s.scalars(select(SkillDailySnapshot.snapshot_date).distinct())))
        return {
            "runs": runs,
            "snapshots_rebuilt": snapshots,
            "evidence_rows": result.evidence_rows,
            "duration_ms": (time.perf_counter_ns() - started) // 1_000_000,
        }
