"""Engine inputs (current raw observations as domain value objects) and derived-table persistence.

Derived tables (evidence, skill_states, skill_daily_snapshots) are fully rewritten by a mentor run; they are
caches of pure functions of the raw tables and can be rebuilt at any time (POST /admin/rebuild).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, aliased

from app.domain.activity.vocabulary import PERSONAL_SEED_VERSION
from app.domain.clock import local_date
from app.domain.evidence.model import (
    AssessmentObservation,
    AssessmentSkillInput,
    AttemptObservation,
    EvidenceRow,
    MockRoundObservation,
    MockRoundSkillInput,
    SkillInfo,
)
from app.domain.gaps.model import Gap
from app.domain.readiness.engine import Condition, Readiness
from app.domain.revision.model import RevisionAction, RevisionItem
from app.domain.skills.state import SkillState as DomainSkillState
from app.models import (
    BehavioralStory,
    Evidence,
    GapState,
    Mock,
    MockRoundRow,
    MockRoundSkill,
    ProblemSkill,
    ReadinessSnapshot,
    RevisionItemAction,
    RevisionItemRow,
    Skill,
    SkillDailySnapshot,
    SkillState,
    StoryCompetency,
)
from app.repositories.activity_repository import ActivityRepository
from app.repositories.assessment_repository import AssessmentRepository


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@dataclass(frozen=True)
class MockRoundFact:
    round_id: int
    mock_id: int
    occurred_on: date
    occurred_at: datetime
    source: str
    is_final_simulation: bool
    round_type: str
    position: int
    round_score: int
    duration_minutes: int
    communication_points: int | None
    skills: tuple[tuple[str, int, bool], ...]  # (skill, outcome_points, is_weakness)


@dataclass(frozen=True)
class EngineInputs:
    skills: Mapping[str, SkillInfo]  # active skills, seed order
    skill_ids: Mapping[str, int]
    attempts: tuple[AttemptObservation, ...]
    assessments: tuple[AssessmentObservation, ...]
    mock_rounds: tuple[MockRoundObservation, ...]


@dataclass(frozen=True)
class StoredState:
    score: int | None
    effective: int | None
    level: int | None
    confidence: str


@dataclass(frozen=True)
class StoredGap:
    priority: int
    status: str


def _condition_json(c: Condition) -> dict[str, object]:
    out = asdict(c)
    out["skills"] = list(c.skills)
    return {k: (v if isinstance(v, int | str | list) or v is None else str(v)) for k, v in out.items()}


def evidence_ref(row: EvidenceRow) -> list[object]:
    """Compact, stable reference to an evidence row: [source_type, source_id, skill]."""
    return [row.source_type, row.source_id, row.skill]


class EvidenceRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    # ------------------------------------------------------------------ inputs
    def engine_inputs(self) -> EngineInputs:
        skills = list(
            self._s.scalars(select(Skill).where(Skill.active.is_(True)).order_by(Skill.position, Skill.id))
        )
        infos = {s.skill_key: SkillInfo(s.skill_key, s.component, s.is_pattern) for s in skills}
        ids = {s.skill_key: s.id for s in skills}
        key_by_id = {s.id: s.skill_key for s in skills}

        attempt_rows = ActivityRepository(self._s).attempts(ascending=True, limit=1_000_000)
        mappings: dict[int, list[tuple[str, int]]] = {}
        problem_ids = sorted({r.problem.id for r in attempt_rows})
        if problem_ids:
            for link in self._s.scalars(
                select(ProblemSkill)
                .where(ProblemSkill.problem_id.in_(problem_ids))
                .order_by(ProblemSkill.problem_id, ProblemSkill.skill_id)
            ):
                if link.skill_id in key_by_id:
                    mappings.setdefault(link.problem_id, []).append(
                        (key_by_id[link.skill_id], link.mapping_weight_bp)
                    )
        attempts = tuple(
            AttemptObservation(
                id=r.attempt.id,
                problem_id=r.problem.id,
                attempted_on=r.attempt.attempted_on,
                attempted_at=aware(r.attempt.attempted_at),
                outcome=r.attempt.outcome,
                seen_elsewhere=r.attempt.seen_elsewhere,
                hints_used=r.attempt.hints_used,
                solution_viewed=r.attempt.solution_viewed,
                pattern_identified=r.attempt.pattern_identified,
                timed=r.attempt.timed,
                time_limit_seconds=r.attempt.time_limit_seconds,
                time_seconds=r.attempt.time_seconds,
                explanation_score=r.attempt.explanation_score,
                complexity_correct=r.attempt.complexity_correct,
                followup_solved=r.attempt.followup_solved,
                execution_rubric=r.attempt.execution_rubric_json,
                mistakes=r.mistakes,
                self_rating_before=r.attempt.self_rating_before,
                difficulty=r.problem.difficulty,
                expected_minutes=r.problem.expected_minutes,
                mappings=tuple(mappings.get(r.problem.id, ())),
                mode=r.attempt.mode,
                revision_item_key=r.attempt.revision_item_key,
                is_canonical=r.problem.is_canonical,
                is_catalog=r.problem.seed_version != PERSONAL_SEED_VERSION,
            )
            for r in attempt_rows
        )

        assessments = tuple(
            AssessmentObservation(
                id=r.assessment.id,
                kind=r.assessment.kind,
                observed_on=r.assessment.observed_on,
                observed_at=aware(r.assessment.observed_at),
                source_key=r.assessment.source_key,
                skills=tuple(
                    AssessmentSkillInput(s.skill, s.outcome_points, s.mapping_weight_bp)
                    for s in r.skills
                    if s.skill in infos
                ),
                notes_used=r.assessment.notes_used,
                reference_used=r.assessment.reference_used,
                hints_used=r.assessment.hints_used,
                timed=r.assessment.timed,
                time_limit_seconds=r.assessment.time_limit_seconds,
                time_seconds=r.assessment.time_seconds,
                followup_points=r.assessment.followup_points,
                communication_points=r.assessment.communication_points,
                peer_evaluated=r.assessment.peer_evaluated,
                applied=r.assessment.applied,
                unseen_variant=r.assessment.unseen_variant,
                difficulty=r.assessment.difficulty,
                familiarity=r.assessment.familiarity,
                study_minutes=r.assessment.study_minutes,
                self_rating_before=r.assessment.self_rating_before,
                revision_item_key=r.assessment.revision_item_key,
            )
            for r in AssessmentRepository(self._s).find(ascending=True, limit=None)
        )
        return EngineInputs(infos, ids, attempts, assessments, self._mock_rounds())

    def mock_facts(self) -> list[MockRoundFact]:
        """Every round of every current (non-superseded) mock, in (occurred_at, mock id, position) order."""
        successor = aliased(Mock)
        mocks = list(
            self._s.scalars(
                select(Mock)
                .outerjoin(successor, successor.supersedes_id == Mock.id)
                .where(successor.id.is_(None))
                .order_by(Mock.occurred_at, Mock.id)
            )
        )
        if not mocks:
            return []
        by_id = {m.id: m for m in mocks}
        rounds = list(
            self._s.scalars(
                select(MockRoundRow)
                .where(MockRoundRow.mock_id.in_(by_id))
                .order_by(MockRoundRow.mock_id, MockRoundRow.position)
            )
        )
        skills: dict[int, list[tuple[str, int, bool]]] = {}
        if rounds:
            for link, key in self._s.execute(
                select(MockRoundSkill, Skill.skill_key)
                .join(Skill, Skill.id == MockRoundSkill.skill_id)
                .where(MockRoundSkill.round_id.in_([r.id for r in rounds]))
                .order_by(MockRoundSkill.round_id, Skill.skill_key)
            ).all():
                skills.setdefault(link.round_id, []).append((key, link.outcome_points, link.is_weakness))
        out = []
        for r in rounds:
            m = by_id[r.mock_id]
            out.append(
                MockRoundFact(
                    round_id=r.id,
                    mock_id=m.id,
                    occurred_on=m.occurred_on,
                    occurred_at=aware(m.occurred_at),
                    source=m.source,
                    is_final_simulation=m.is_final_simulation,
                    round_type=r.round_type,
                    position=r.position,
                    round_score=r.round_score,
                    duration_minutes=r.duration_minutes,
                    communication_points=r.communication_points,
                    skills=tuple(skills.get(r.id, ())),
                )
            )
        return out

    def _mock_rounds(self) -> tuple[MockRoundObservation, ...]:
        return tuple(
            MockRoundObservation(
                id=f.round_id,
                occurred_on=f.occurred_on,
                occurred_at=f.occurred_at,
                source=f.source,
                round_type=f.round_type,
                skills=tuple(MockRoundSkillInput(k, p, w) for k, p, w in f.skills),
                communication_points=f.communication_points,
            )
            for f in self.mock_facts()
        )

    def story_facts(self) -> list[tuple[int, date, str | None, list[str]]]:
        """(story id, created local date, first competency, all competencies) for non-archived stories."""
        stories = list(
            self._s.scalars(
                select(BehavioralStory)
                .where(BehavioralStory.archived_at.is_(None))
                .order_by(BehavioralStory.id)
            )
        )
        comps: dict[int, list[str]] = {}
        for link, key in self._s.execute(
            select(StoryCompetency, Skill.skill_key)
            .join(Skill, Skill.id == StoryCompetency.skill_id)
            .order_by(StoryCompetency.story_id, StoryCompetency.position)
        ).all():
            comps.setdefault(link.story_id, []).append(key)
        tz = ActivityRepository(self._s).timezone() or "UTC"
        return [
            (
                s.id,
                local_date(aware(s.created_at), tz),
                next(iter(comps.get(s.id, [])), None),
                comps.get(s.id, []),
            )
            for s in stories
        ]

    # ------------------------------------------------------------------ derived tables
    def stored_states(self) -> dict[int, StoredState]:
        return {
            s.skill_id: StoredState(s.score, s.effective_score, s.level, s.confidence)
            for s in self._s.scalars(select(SkillState))
        }

    def replace_evidence(
        self, rows: Sequence[EvidenceRow], skill_ids: Mapping[str, int], ruleset_version: str
    ) -> None:
        self._s.execute(delete(Evidence).where(Evidence.ruleset_version == ruleset_version))
        if not rows:
            return
        self._s.execute(
            insert(Evidence),
            [
                {
                    "ruleset_version": ruleset_version,
                    "source_type": r.source_type,
                    "source_id": r.source_id,
                    "skill_id": skill_ids[r.skill],
                    "rule": r.rule,
                    "kind": r.kind,
                    "level": r.level,
                    "outcome_points": r.outcome_points,
                    "is_scoring": r.is_scoring,
                    "observed_on": r.observed_on,
                    "observed_at": r.observed_at.astimezone(UTC).replace(tzinfo=None),
                    "difficulty_bp": r.difficulty_bp,
                    "mapping_bp": r.mapping_bp,
                    "is_primary": r.is_primary,
                    "source_key": r.source_key,
                    "timed": r.timed,
                    "time_ratio_bp": r.time_ratio_bp,
                    "within_limit": r.within_limit,
                    "depth_points": r.depth_points,
                    "communication_points": r.communication_points,
                    "self_rating_before": r.self_rating_before,
                    "pattern_identified": r.pattern_identified,
                    "is_unseen": r.is_unseen,
                    "is_weakness": r.is_weakness,
                    "familiarity": r.familiarity,
                    "study_minutes": r.study_minutes,
                }
                for r in rows
            ],
        )

    def replace_states(
        self,
        states: Mapping[str, DomainSkillState],
        skill_ids: Mapping[str, int],
        *,
        run_id: int,
        as_of: date,
        ruleset_version: str,
        gaps: Mapping[str, Gap] | None = None,
    ) -> None:
        gaps = gaps or {}
        self._s.execute(delete(SkillState))
        self._s.execute(delete(SkillDailySnapshot).where(SkillDailySnapshot.snapshot_date == as_of))
        if not states:
            return
        self._s.execute(
            insert(SkillState),
            [
                {
                    "skill_id": skill_ids[key],
                    "run_id": run_id,
                    "as_of_date": as_of,
                    "score": st.score,
                    "level": st.level,
                    "quality": st.quality,
                    "confidence": st.confidence,
                    "effective_score": st.effective_score,
                    "peak_score": st.peak_score,
                    "evidence_count": st.evidence_count,
                    "distinct_sources": st.distinct_sources,
                    "last_practiced_on": st.last_practiced_on,
                    "last_observed_on": st.last_observed_on,
                    "label": st.label,
                    "reality_capped": st.reality_capped,
                    "declared_unknown": st.declared_unknown,
                    "considered_evidence_json": [evidence_ref(r) for r in st.considered],
                    "qualifying_evidence_json": [evidence_ref(r) for r in st.qualifying],
                    "ruleset_version": ruleset_version,
                }
                for key, st in states.items()
            ],
        )
        self._s.execute(
            insert(SkillDailySnapshot),
            [
                {
                    "snapshot_date": as_of,
                    "skill_id": skill_ids[key],
                    "run_id": run_id,
                    "score": st.score,
                    "effective_score": st.effective_score,
                    "level": st.level,
                    "confidence": st.confidence,
                    "priority": gaps[key].priority if key in gaps else None,
                    "status": gaps[key].status if key in gaps else None,
                }
                for key, st in states.items()
            ],
        )

    def stored_gaps(self) -> dict[int, StoredGap]:
        return {g.skill_id: StoredGap(g.priority, g.status) for g in self._s.scalars(select(GapState))}

    def replace_gaps(
        self,
        gaps: Mapping[str, Gap],
        skill_ids: Mapping[str, int],
        *,
        run_id: int,
        goal_id: int | None,
        as_of: date,
        ruleset_version: str,
    ) -> None:
        self._s.execute(delete(GapState))
        if not gaps:
            return
        self._s.execute(
            insert(GapState),
            [
                {
                    "skill_id": skill_ids[key],
                    "run_id": run_id,
                    "goal_id": goal_id,
                    "as_of_date": as_of,
                    "status": g.status,
                    "priority": g.priority,
                    "rank": g.rank,
                    "raw_gap": g.raw_gap,
                    "severity": g.severity,
                    "pressure_bp": g.pressure_bp,
                    "primary_gap_type": g.primary_gap_type,
                    "gap_types_json": list(g.gap_types),
                    "reason_codes_json": list(g.reason_codes),
                    "blocked_by_json": [
                        {"skill": b.skill, "score": b.score, "min_score": b.min_score} for b in g.blocked_by
                    ],
                    "parked_reason": g.parked_reason,
                    "focus_stage": g.focus_stage,
                    "focus_skill": g.focus_skill,
                    "metrics_json": g.metrics,
                    "evidence_json": {k: [list(ref) for ref in v] for k, v in g.evidence.items()},
                    "ruleset_version": ruleset_version,
                }
                for key, g in gaps.items()
                if key in skill_ids
            ],
        )

    # ------------------------------------------------------------------ revision
    def revision_actions(self) -> list[RevisionAction]:
        return [
            RevisionAction(a.id, a.item_key, a.action, a.reason, a.action_on, aware(a.created_at))
            for a in self._s.scalars(select(RevisionItemAction).order_by(RevisionItemAction.id))
        ]

    def stored_revision_items(self) -> dict[str, tuple[str, str | None, int]]:
        return {
            i.item_key: (i.state, i.due_date.isoformat() if i.due_date else None, i.interval_index)
            for i in self._s.scalars(select(RevisionItemRow))
        }

    def replace_revision_items(
        self, items: Mapping[str, RevisionItem], skill_ids: Mapping[str, int], *, run_id: int
    ) -> None:
        self._s.execute(delete(RevisionItemRow))
        rows = [
            {
                "item_key": i.item_key,
                "item_type": i.item_type,
                "skill_id": skill_ids[i.skill],
                "subject_ref": i.subject_ref,
                "ladder": i.ladder,
                "state": i.state,
                "suspend_reason": i.suspend_reason,
                "interval_index": i.interval_index,
                "due_date": i.due_date,
                "lapses": i.lapses,
                "needs_reinforcement": i.needs_reinforcement,
                "minutes": i.minutes,
                "created_on": i.created_on,
                "last_reviewed_on": i.last_reviewed_on,
                "suspended_on": i.suspended_on,
                "run_id": run_id,
            }
            for i in items.values()
            if i.skill in skill_ids
        ]
        if rows:
            self._s.execute(insert(RevisionItemRow), rows)

    # ------------------------------------------------------------------ readiness
    def previous_readiness_states(self, as_of: date, days: int = 30) -> dict[date, str]:
        rows = self._s.execute(
            select(ReadinessSnapshot.snapshot_date, ReadinessSnapshot.state).where(
                ReadinessSnapshot.snapshot_date < as_of,
                ReadinessSnapshot.snapshot_date >= as_of - timedelta(days=days),
            )
        ).all()
        return {d: str(s) for d, s in rows}

    def readiness_snapshot(self, day: date) -> ReadinessSnapshot | None:
        return self._s.get(ReadinessSnapshot, day)

    def readiness_history(self, date_from: date, date_to: date) -> list[ReadinessSnapshot]:
        return list(
            self._s.scalars(
                select(ReadinessSnapshot)
                .where(
                    ReadinessSnapshot.snapshot_date >= date_from, ReadinessSnapshot.snapshot_date <= date_to
                )
                .order_by(ReadinessSnapshot.snapshot_date)
            )
        )

    def replace_readiness_snapshot(self, r: Readiness, *, run_id: int, ruleset_version: str) -> None:
        self._s.execute(delete(ReadinessSnapshot).where(ReadinessSnapshot.snapshot_date == r.as_of_date))
        self._s.add(
            ReadinessSnapshot(
                snapshot_date=r.as_of_date,
                run_id=run_id,
                state=r.state,
                weighted_score=r.weighted_score,
                limiting_component=r.limiting_component,
                simulation_eligible=r.simulation_eligible,
                lapsed=r.lapsed,
                components_json=[dict(c) for c in r.components],
                gates_json=[asdict(g) for g in r.gates],
                blockers_json=[_condition_json(c) for c in r.blockers],
                all_failing_json=[_condition_json(c) for c in r.all_failing],
                ruleset_version=ruleset_version,
            )
        )

    def gaps(self) -> dict[int, GapState]:
        return {g.skill_id: g for g in self._s.scalars(select(GapState))}

    # ------------------------------------------------------------------ reads
    def evidence_for_skill(self, skill_id: int, ruleset_version: str, limit: int) -> list[Evidence]:
        return list(
            self._s.scalars(
                select(Evidence)
                .where(Evidence.skill_id == skill_id, Evidence.ruleset_version == ruleset_version)
                .order_by(Evidence.observed_at.desc(), Evidence.source_type, Evidence.source_id.desc())
                .limit(limit)
            )
        )

    def states(self) -> dict[int, SkillState]:
        return {s.skill_id: s for s in self._s.scalars(select(SkillState))}
