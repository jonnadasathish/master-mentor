"""Learning layer orchestration (LEARNING_ENGINE). Loads data, calls the pure learning domain, records
completions
through the existing observation services. No new evidence rule lives here."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.catalog import vocabulary as v
from app.domain.clock import Clock
from app.domain.learning import vocabulary as lv
from app.domain.learning.coverage import SkillFacts, coverage_report, summarize_coverage
from app.domain.learning.evidence import CompletionError, Graded, Submission, grade_completion, rubric_of
from app.domain.learning.model import ContentItem, LearningCatalog
from app.domain.learning.practice import AttemptFact, ProblemRef, problem_state, resolve_practice
from app.domain.learning.progress import ContentProgress, content_progress, pass_mark
from app.domain.learning.session import ProblemOption, StepState, compose_session, summarize
from app.errors import AppError
from app.models import (
    AuditLog,
    LearningSession,
    LearningSessionStep,
    PlanItemRow,
    Problem,
    ProblemAttempt,
    ProblemSkill,
    Skill,
)
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.learning_repository import LearningRepository
from app.schemas.assessment import AssessmentInput
from app.schemas.catalog import SkillSummary
from app.schemas.envelope import ErrorCode
from app.schemas.learning import (
    CompletionIn,
    CompletionOut,
    ContentDetail,
    ContentSummary,
    CoverageOut,
    CoverageRowOut,
    NextActionOut,
    PracticeOut,
    ProblemBrief,
    ProgressOut,
    QuestionResultOut,
    RelatedProblemOut,
    SessionOut,
    SessionStartIn,
    SkillLearningOut,
    StepCompleteIn,
    StepOut,
    StepPreview,
    StepResultOut,
    TopicOut,
    TopicSkillOut,
    TrackDetail,
    TrackOut,
)
from app.services.activity_service import ActivityService, attempt_fact, platform_url, problem_key
from app.services.assessment_service import AssessmentService
from app.services.catalog_service import CatalogService

# Choice answers and explanations stay on the server until the check is graded. A short answer keeps its model
# answer: the learner grades their own answer against it before submitting.
HIDDEN_QUESTION_FIELDS = ("answer", "explanation")
DEFAULT_PROBLEM_MINUTES = {"EASY": 15, "MEDIUM": 30, "HARD": 45}  # DEFAULT_EXPECTED_MINUTES (seed comment)


def _naive_now(clock: Clock) -> Any:
    return clock.now_utc().astimezone(UTC).replace(tzinfo=None)


def _not_found(what: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, f"{what} not found.", 404)


def _invalid(message: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError(ErrorCode.INVALID_STATE, message, 409, details or {})


class LearningService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock
        self._repo = LearningRepository(session)
        self._catalog_repo = CatalogRepository(session)
        self._catalog = CatalogService(self._catalog_repo)
        self._evidence = EvidenceRepository(session)
        self._learning: LearningCatalog | None = None
        self._skills: dict[str, SkillSummary] | None = None
        self._all_progress: dict[str, ContentProgress] | None = None
        self._by_skill: dict[str, list[ProblemRef]] | None = None

    # ----------------------------------------------------------------------------------------- loading
    def learning(self) -> LearningCatalog:
        if self._learning is None:
            self._catalog.seed_version()  # 409 when no catalog is loaded
            self._learning = self._repo.catalog()
        return self._learning

    def skills(self) -> dict[str, SkillSummary]:
        if self._skills is None:
            self._skills = {s.key: s for s in self._catalog.skills()}
        return self._skills

    def _components(self) -> dict[str, str]:
        return {k: s.component for k, s in self.skills().items()}

    def _progress(self, content_key: str | None = None) -> dict[str, ContentProgress]:
        if content_key is not None:
            return content_progress(self._repo.content_observations(content_key), self.learning().by_key)
        if self._all_progress is None:  # one read per request; writes go through _record, which resets it
            self._all_progress = content_progress(self._repo.content_observations(), self.learning().by_key)
        return self._all_progress

    def session_for_plan_item(self, plan_item_id: int) -> LearningSession | None:
        return self._repo.session_for_plan_item(plan_item_id)

    def _item(self, key: str) -> ContentItem:
        item = self.learning().by_key.get(key)
        if item is None:
            raise _not_found(f"Content {key!r}")
        return item

    def _skill_ids(self) -> dict[str, int]:
        return {s.skill_key: s.id for s, _ in self._catalog_repo.skills(include_inactive=True)}

    # --------------------------------------------------------------------------------------- read models
    @staticmethod
    def _progress_out(p: ContentProgress | None) -> ProgressOut | None:
        if p is None:
            return None
        return ProgressOut(
            completions=p.completions,
            last_points=p.last_points,
            best_points=p.best_points,
            last_on=p.last_on,
            passed=p.passed,
            milestones_done=list(p.milestones_done),
            defended=p.defended,
        )

    def summary(self, item: ContentItem, progress: Mapping[str, ContentProgress]) -> ContentSummary:
        return ContentSummary(
            key=item.key,
            type=item.type,
            title=item.title,
            minutes=item.minutes,
            difficulty=item.difficulty,
            skills=list(item.skills),
            tab=lv.TAB_OF_TYPE[item.type],
            stages=list(item.stages),
            observation_kind=item.observation_kind,
            time_limit_seconds=item.time_limit_seconds,
            progress=self._progress_out(progress.get(item.key)),
        )

    def content(self, key: str) -> ContentDetail:
        item = self._item(key)
        progress = self._progress(key)
        body: dict[str, Any] = dict(item.body)
        if item.type in ("concept_check", "quiz"):
            body["questions"] = [
                {k: v for k, v in q.items() if k not in HIDDEN_QUESTION_FIELDS}
                for q in item.body["questions"]
            ]
        topic = self.learning().topic_of(item.primary_skill)
        return ContentDetail(
            **self.summary(item, progress).model_dump(),
            body=body,
            rubric=[dict(r) for r in rubric_of(item)],
            pass_points=pass_mark(item),
            problems=self._briefs(item.problem_ids),
            topic={"key": topic.key, "title": topic.title, "track": topic.track} if topic else None,
        )

    # --------------------------------------------------------------------------------------- completion
    def _record(self, item: ContentItem, inp: CompletionIn) -> tuple[Graded, Any]:
        sub = Submission(
            answers=inp.answers,
            self_grades=dict(inp.self_grades),
            ratings=dict(inp.ratings),
            followups=dict(inp.followups),
            minutes=inp.minutes,
            notes_used=inp.notes_used,
            reference_used=inp.reference_used,
            hints_used=inp.hints_used,
            timed=inp.timed,
            time_seconds=inp.time_seconds,
            milestone=inp.milestone,
            defense=inp.defense,
            notes=inp.notes,
        )
        try:
            graded = grade_completion(item, sub, self._components())
        except CompletionError as exc:
            raise AppError(ErrorCode.VALIDATION_ERROR, str(exc), 422) from exc
        payload = {k: v for k, v in graded.payload.items() if v is not None}
        payload["client_request_id"] = inp.client_request_id
        try:
            assessment = AssessmentInput.model_validate(payload)
        except ValidationError as exc:  # a seed/validator gap, never the learner's fault
            raise AppError(ErrorCode.VALIDATION_ERROR, f"Cannot record {item.key}: {exc}", 422) from exc
        recorded = AssessmentService(self._s, self._clock).record(assessment)
        self._all_progress = None
        return graded, recorded

    def _completion_out(self, item: ContentItem, graded: Graded, recorded: Any) -> CompletionOut:
        questions = []
        if graded.check is not None:
            questions = [
                QuestionResultOut(
                    id=q.id,
                    kind=q.kind,
                    earned=q.earned,
                    chosen=list(q.chosen),
                    answer=list(q.answer),
                    explanation=q.explanation,
                    model_answer=q.model_answer,
                )
                for q in graded.check.questions
            ]
        return CompletionOut(
            content_key=item.key,
            points=graded.points,
            passed=graded.passed,
            followup_points=graded.followup_points,
            questions=questions,
            observation=recorded,
            progress=self._progress_out(self._progress(item.key).get(item.key)),
        )

    def complete(self, key: str, inp: CompletionIn) -> CompletionOut:
        item = self._item(key)
        if item.type in lv.PROBLEM_TYPES:
            raise _invalid("Guided and timed problems are recorded from the problem page.")
        graded, recorded = self._record(item, inp)
        return self._completion_out(item, graded, recorded)

    # ---------------------------------------------------------------------------------------- problems
    def _attempt_facts(self, problem_ids: Sequence[int]) -> dict[int, list[AttemptFact]]:
        if not problem_ids:
            return {}
        successor = select(ProblemAttempt.supersedes_id).where(ProblemAttempt.supersedes_id.is_not(None))
        rows = self._s.scalars(
            select(ProblemAttempt).where(
                ProblemAttempt.problem_id.in_(problem_ids), ProblemAttempt.id.notin_(successor)
            )
        )
        out: dict[int, list[AttemptFact]] = {}
        for attempt in rows:
            out.setdefault(attempt.problem_id, []).append(attempt_fact(attempt))
        return out

    def _briefs(self, problem_ids: Sequence[int]) -> list[ProblemBrief]:
        if not problem_ids:
            return []
        problems = {p.id: p for p in self._s.scalars(select(Problem).where(Problem.id.in_(problem_ids)))}
        facts = self._attempt_facts(list(problems))
        return [
            ProblemBrief(
                id=p.id,
                key=problem_key(p),
                title=p.title,
                difficulty=p.difficulty,
                expected_minutes=p.expected_minutes,
                url=platform_url(p),
                practice_state=problem_state(facts.get(p.id, [])),
            )
            for pid in problem_ids
            if (p := problems.get(pid)) is not None and p.active
        ]

    def _problems_by_skill(self) -> dict[str, list[ProblemRef]]:
        if self._by_skill is not None:
            return self._by_skill
        out: dict[str, list[ProblemRef]] = {}
        rows = self._s.execute(
            select(ProblemSkill, Problem, Skill.skill_key)
            .join(Problem, Problem.id == ProblemSkill.problem_id)
            .join(Skill, Skill.id == ProblemSkill.skill_id)
            .where(Problem.active.is_(True))
            .order_by(Problem.id)
        )
        for mapping, problem, key in rows:
            out.setdefault(key, []).append(
                ProblemRef(
                    problem.id,
                    problem.title,
                    problem.difficulty,
                    problem.is_canonical,
                    mapping.mapping_weight_bp,
                )
            )
        self._by_skill = out
        return out

    # ------------------------------------------------------------------------------------ skill learning
    def skill_learning(self, key: str) -> SkillLearningOut:
        skills = self.skills()
        summary = skills.get(key)
        if summary is None:
            raise _not_found(f"Skill {key!r}")
        learning = self.learning()
        progress = self._progress()
        items = learning.for_skill(key)
        tabs: dict[str, list[ContentSummary]] = {t: [] for t in lv.TABS}
        for item in items:
            tabs[lv.TAB_OF_TYPE[item.type]].append(self.summary(item, progress))

        detail = self._catalog.skill(key)
        prerequisites = [p.key for p in self._catalog.prerequisites(key).prerequisites]
        dependents = [d.key for d in detail.dependents]
        group_skills = [s.key for s in skills.values() if s.group == summary.group]
        problems_by_skill = self._problems_by_skill()
        content_by_skill = {
            k: learning.for_skill(k) for k in {key, *prerequisites, *dependents, *group_skills}
        }
        resolution = resolve_practice(
            skill=key,
            component=summary.component,
            prerequisites=prerequisites,
            dependents=dependents,
            group_skills=group_skills,
            problems_by_skill=problems_by_skill,
            content_by_skill=content_by_skill,
        )
        related_ids = [r.problem.id for r in resolution.related]
        briefs = {b.id: b for b in self._briefs([p.id for p in resolution.direct] + related_ids)}
        practice = PracticeOut(
            case=resolution.case,
            direct=[briefs[p.id] for p in resolution.direct if p.id in briefs],
            related=[
                RelatedProblemOut(
                    problem=briefs[r.problem.id],
                    via_skill=r.via_skill,
                    via_name=skills[r.via_skill].name if r.via_skill in skills else r.via_skill,
                    relation=r.relation,
                )
                for r in resolution.related
                if r.problem.id in briefs
            ],
            fallback_skill=resolution.fallback_skill,
            fallback_name=skills[resolution.fallback_skill].name
            if resolution.fallback_skill in skills
            else None,
            fallback_relation=resolution.fallback_relation,
        )

        ids = self._skill_ids()
        state = self._evidence.states().get(ids[key])
        gap = self._evidence.gaps().get(ids[key])
        topic = learning.topic_of(key)
        same_topic = [s for s in (topic.skills if topic else ()) if s != key]
        related = (
            [
                {"key": k, "name": skills[k].name, "relation": "PREREQUISITE"}
                for k in prerequisites
                if k in skills
            ]
            + [{"key": k, "name": skills[k].name, "relation": "DEPENDENT"} for k in dependents if k in skills]
            + [
                {"key": k, "name": skills[k].name, "relation": "SAME_TOPIC"}
                for k in same_topic
                if k in skills
            ]
        )
        rows = self._coverage_rows()
        coverage = next((r.coverage_state for r in rows if r.skill_key == key), "CONTENT_GAP")
        profile = self._profile_config()
        rounds = sorted(
            {
                str(r["round_type"])
                for r in profile.get("interview_loop", [])
                if r.get("round_type") and summary.component in (r.get("components") or [])
            }
        )
        tiers = profile.get("tiers", {})
        tier_label = (
            tiers.get(summary.tier, {}).get("label") if summary.tier and isinstance(tiers, dict) else None
        )
        return SkillLearningOut(
            skill={
                "key": key,
                "name": summary.name,
                "component": summary.component,
                "group": summary.group,
                "tier": summary.tier,
                "importance": summary.importance,
                "target_score": summary.target_score,
                "required": summary.required,
            },
            why_it_matters={
                "tier_label": tier_label,
                "importance": summary.importance,
                "target_score": summary.target_score,
                "rounds": rounds,
                "unlocks": dependents,
                "topic": {"key": topic.key, "title": topic.title, "track": topic.track} if topic else None,
            },
            state={
                "score": state.score if state else None,
                "effective_score": state.effective_score if state else None,
                "label": state.label if state else "UNASSESSED",
                "confidence": state.confidence if state else "NONE",
                "assessed": bool(state and state.confidence != "NONE"),
                "gap_status": gap.status if gap else None,
                "gap_type": gap.primary_gap_type if gap else None,
                "focus_stage": gap.focus_stage if gap else None,
                "focus_skill": gap.focus_skill if gap else None,
                "reason_codes": list(gap.reason_codes_json) if gap else [],
            },
            tabs=tabs,
            practice=practice,
            related_skills=related,
            next_action=self._next_action(key, gap),
            coverage_state=coverage,
        )

    def _profile_config(self) -> dict[str, Any]:
        profiles = self._catalog_repo.profiles()
        return dict(profiles[0].config_json) if profiles else {}

    def _next_action(self, key: str, gap: Any) -> NextActionOut:
        ids = self._skill_ids()
        active = self._repo.active_session(ids[key])
        if active is not None:
            out = self.session(active.id)
            return NextActionOut(
                kind="RESUME_SESSION",
                stage=active.stage,
                reason="ACTIVE_SESSION",
                session_id=active.id,
                minutes=out.minutes,
                steps=[],
                fallback_skill=None,
            )
        if gap is not None and gap.focus_skill and gap.focus_skill != key:
            return NextActionOut(
                kind="FALLBACK",
                stage=gap.focus_stage,
                reason="PREREQUISITE_FIRST",
                session_id=None,
                minutes=None,
                steps=[],
                fallback_skill=gap.focus_skill,
            )
        stage, reason = self.stage_for(gap)
        steps = self.preview(key, stage, None)
        if steps:
            return NextActionOut(
                kind="START_SESSION",
                stage=stage,
                reason=reason,
                session_id=None,
                minutes=sum(s.minutes for s in steps),
                steps=steps,
                fallback_skill=None,
            )
        return NextActionOut(
            kind="NONE",
            stage=stage,
            reason="NO_CONTENT",
            session_id=None,
            minutes=None,
            steps=[],
            fallback_skill=None,
        )

    @staticmethod
    def stage_for(gap: Any) -> tuple[str, str]:
        """The mentor's own focus stage when it has one; LEARN for an unmeasured skill; RECALL to maintain."""
        if gap is not None and gap.focus_stage:
            return str(gap.focus_stage), "GAP_FOCUS"
        if gap is None or gap.status == "UNASSESSED":
            return "LEARN", "UNASSESSED"
        return "RECALL", "MAINTAIN"

    def preview(self, key: str, stage: str, budget: int | None) -> list[StepPreview]:
        steps = self._compose(key, stage, budget)
        return [
            StepPreview(
                position=s.position,
                kind=s.kind,
                title=s.title,
                minutes=s.minutes,
                content_key=s.content_key,
                content_type=s.content_type,
                problem_id=s.problem_id,
            )
            for s in steps
        ]

    def _compose(self, key: str, stage: str, budget: int | None) -> tuple[Any, ...]:
        learning = self.learning()
        progress = self._progress()
        direct = self._problems_by_skill().get(key, [])
        problems = (
            self._s.scalars(select(Problem).where(Problem.id.in_([p.id for p in direct]))).all()
            if direct
            else []
        )
        options = [
            ProblemOption(
                p.id,
                p.title,
                p.difficulty,
                p.expected_minutes or DEFAULT_PROBLEM_MINUTES.get(p.difficulty, 30),
            )
            for p in sorted(problems, key=lambda p: p.id)
        ]
        attempted = set(self._attempt_facts([p.id for p in problems]))
        return compose_session(
            stage=stage,
            content=learning.for_skill(key),
            problems=options,
            done=frozenset(k for k, p in progress.items() if p.completions),
            attempted=attempted,
            budget_minutes=budget,
        )

    # ------------------------------------------------------------------------------------- curriculum
    def _coverage_rows(self) -> tuple[Any, ...]:
        skills = self.skills()
        facts = [
            SkillFacts(s.key, s.name, s.component, s.tier, s.importance or 0, bool(s.required))
            for s in skills.values()
        ]
        difficulties: dict[str, list[str]] = {}
        for key, refs in self._problems_by_skill().items():
            difficulties[key] = [r.difficulty for r in refs]
        rounds: dict[str, list[str]] = {}
        for r in self._profile_config().get("interview_loop", []):
            if not r.get("round_type"):
                continue
            for c in r.get("components") or []:
                if r["round_type"] not in rounds.setdefault(c, []):
                    rounds[c].append(str(r["round_type"]))
        return coverage_report(facts, self.learning(), difficulties, rounds)

    def coverage(self) -> CoverageOut:
        rows = self._coverage_rows()
        counts: dict[str, int] = {t: 0 for t in lv.CONTENT_TYPES}
        for c in self.learning().content:
            counts[c.type] += 1
        return CoverageOut(
            summary=summarize_coverage(rows),
            content_counts=counts,
            rows=[
                CoverageRowOut(
                    **{**r.__dict__, "tracks": list(r.tracks), "mock_coverage": list(r.mock_coverage)}
                )
                for r in rows
            ],
        )

    def curriculum(self) -> list[TrackOut]:
        return [self._track_out(t.key) for t in self.learning().tracks]

    def _track_out(self, track_key: str) -> TrackOut:
        learning = self.learning()
        track = next((t for t in learning.tracks if t.key == track_key), None)
        if track is None:
            raise _not_found(f"Track {track_key!r}")
        skills = self.skills()
        progress = self._progress()
        ids = self._skill_ids()
        states = self._evidence.states()
        gaps = self._evidence.gaps()
        coverage = {r.skill_key: r.coverage_state for r in self._coverage_rows()}
        topics = []
        keys: set[str] = set()
        for topic in track.topics:
            rows = []
            for k in topic.skills:
                s = skills.get(k)
                if s is None:
                    continue
                items = learning.for_skill(k)
                keys.update(c.key for c in items)
                state, gap = states.get(ids[k]), gaps.get(ids[k])
                rows.append(
                    TopicSkillOut(
                        key=k,
                        name=s.name,
                        tier=s.tier,
                        required=s.required,
                        score=state.effective_score if state else None,
                        target_score=s.target_score,
                        label=state.label if state else "UNASSESSED",
                        status=gap.status if gap else None,
                        content_count=len(items),
                        done_count=sum(1 for c in items if c.key in progress),
                        coverage_state=coverage.get(k, "CONTENT_GAP"),
                    )
                )
            topics.append(TopicOut(key=topic.key, title=topic.title, summary=topic.summary, skills=rows))
        return TrackOut(
            key=track.key,
            title=track.title,
            summary=track.summary,
            components=list(track.components),
            topics=topics,
            content_count=len(keys),
            done_count=sum(1 for k in keys if k in progress),
        )

    def track(self, track_key: str) -> TrackDetail:
        out = self._track_out(track_key)
        learning = self.learning()
        progress = self._progress()
        content: dict[str, list[ContentSummary]] = {}
        track = next(t for t in learning.tracks if t.key == track_key)
        for topic in track.topics:
            seen: set[str] = set()
            items: list[ContentSummary] = []
            for k in topic.skills:
                for c in learning.for_skill(k):
                    if c.key not in seen and c.skills[0] in topic.skills:
                        seen.add(c.key)
                        items.append(self.summary(c, progress))
            items.sort(key=lambda c: learning.by_key[c.key].position)
            content[topic.key] = items
        return TrackDetail(**out.model_dump(), content=content)

    # --------------------------------------------------------------------------------------- sessions
    def _session_out(self, row: LearningSession, steps: Sequence[LearningSessionStep]) -> SessionOut:
        skill = self._s.get(Skill, row.skill_id)
        assert skill is not None
        state = self._evidence.states().get(row.skill_id)
        briefs = {b.id: b for b in self._briefs([s.problem_id for s in steps if s.problem_id is not None])}
        content = self.learning().by_key
        summary = summarize([StepState(s.position, s.status, s.points, s.passed) for s in steps])
        return SessionOut(
            id=row.id,
            skill=skill.skill_key,
            skill_name=skill.name,
            stage=row.stage,
            status=row.status,
            outcome=row.outcome,
            plan_item_id=row.plan_item_id,
            budget_minutes=row.budget_minutes,
            minutes=sum(s.minutes for s in steps),
            started_at=row.started_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            completed_at=(
                row.completed_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
                if row.completed_at
                else None
            ),
            next_position=summary.next_position if row.status == "ACTIVE" else None,
            steps=[
                StepOut(
                    position=s.position,
                    kind=s.step_kind,
                    title=s.title,
                    minutes=s.minutes,
                    status=s.status,
                    content_key=s.content_key,
                    content_type=content[s.content_key].type
                    if s.content_key and s.content_key in content
                    else None,
                    problem=briefs.get(s.problem_id) if s.problem_id is not None else None,
                    observation_type=s.observation_type,
                    observation_id=s.observation_id,
                    points=s.points,
                    passed=s.passed,
                    reflection=s.reflection,
                )
                for s in steps
            ],
            before={"score": row.start_score, "level": row.start_level},
            after={
                "score": state.effective_score if state else None,
                "level": state.level if state else None,
            },
        )

    def session(self, session_id: int) -> SessionOut:
        row = self._repo.session(session_id)
        if row is None:
            raise _not_found(f"Learning session {session_id}")
        return self._session_out(row, self._repo.steps(session_id))

    def sessions(self, status: str | None) -> list[SessionOut]:
        return [self._session_out(r, self._repo.steps(r.id)) for r in self._repo.sessions(status=status)]

    def _audit(self, entity_id: int, action: str, payload: dict[str, Any]) -> None:
        self._s.add(
            AuditLog(
                at=_naive_now(self._clock),
                entity_type="learning_session",
                entity_id=str(entity_id),
                action=action,
                payload_json=payload,
            )
        )

    def start_session(self, inp: SessionStartIn) -> SessionOut:
        ids = self._skill_ids()
        if inp.skill not in ids or inp.skill not in self.skills():
            raise _not_found(f"Skill {inp.skill!r}")
        skill_id = ids[inp.skill]
        plan_item: PlanItemRow | None = None
        if inp.plan_item_id is not None:
            plan_item = self._s.get(PlanItemRow, inp.plan_item_id)
            if plan_item is None:
                raise _not_found(f"Plan item {inp.plan_item_id}")
            existing = self._repo.session_for_plan_item(plan_item.id)
            if existing is not None and existing.status == "ACTIVE":
                return self.session(existing.id)
        active = self._repo.active_session(skill_id)
        if active is not None:
            return self.session(active.id)  # resume: one active session per skill
        gap = self._evidence.gaps().get(skill_id)
        stage = inp.stage or (plan_item.stage if plan_item is not None and plan_item.stage else None)
        if stage is None:
            stage = self.stage_for(gap)[0]
        if stage not in v.STAGES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown stage {stage!r}", 422)
        budget = inp.budget_minutes or (plan_item.minutes if plan_item is not None else None)
        steps = self._compose(inp.skill, stage, budget)
        if not steps:
            raise _invalid(
                "There is no learning content for this skill yet.",
                {"skill": inp.skill, "stage": stage, "reason": "NO_CONTENT"},
            )
        state = self._evidence.states().get(skill_id)
        now = _naive_now(self._clock)
        row = LearningSession(
            skill_id=skill_id,
            stage=stage,
            status="ACTIVE",
            plan_item_id=plan_item.id if plan_item is not None else None,
            budget_minutes=budget,
            start_score=state.effective_score if state else None,
            start_level=state.level if state else None,
            outcome=None,
            seed_version=self._catalog.seed_version(),
            started_at=now,
            completed_at=None,
        )
        self._repo.add_session(
            row,
            [
                LearningSessionStep(
                    position=s.position,
                    step_kind=s.kind,
                    content_key=s.content_key,
                    problem_id=s.problem_id,
                    title=s.title[:200],
                    minutes=s.minutes,
                    status="PENDING",
                )
                for s in steps
            ],
        )
        self._audit(
            row.id,
            "START_LEARNING_SESSION",
            {
                "skill": inp.skill,
                "stage": stage,
                "plan_item_id": row.plan_item_id,
                "steps": [
                    s.content_key or (f"problem:{s.problem_id}" if s.problem_id else s.kind) for s in steps
                ],
            },
        )
        self._s.commit()
        return self.session(row.id)

    def _active_step(self, session_id: int, position: int) -> tuple[LearningSession, LearningSessionStep]:
        row = self._repo.session(session_id)
        if row is None:
            raise _not_found(f"Learning session {session_id}")
        if row.status != "ACTIVE":
            raise _invalid(f"Learning session {session_id} is {row.status}.")
        step = next((s for s in self._repo.steps(session_id) if s.position == position), None)
        if step is None:
            raise _not_found(f"Step {position} of session {session_id}")
        if step.status != "PENDING":
            raise _invalid(f"Step {position} is already {step.status}.")
        return row, step

    def complete_step(self, session_id: int, position: int, inp: StepCompleteIn) -> StepResultOut:
        row, step = self._active_step(session_id, position)
        completion: CompletionOut | None = None
        attempt_id: int | None = None
        if step.step_kind == "CONTENT":
            if inp.completion is None or step.content_key is None:
                raise AppError(ErrorCode.VALIDATION_ERROR, "This step needs a completion.", 422)
            item = self._item(step.content_key)
            graded, recorded = self._record(item, inp.completion)
            completion = self._completion_out(item, graded, recorded)
            step.observation_type, step.observation_id = "ASSESSMENT", recorded.id
            step.points, step.passed = graded.points, graded.passed
        elif step.step_kind == "PROBLEM":
            if inp.attempt is None or step.problem_id is None:
                raise AppError(ErrorCode.VALIDATION_ERROR, "This step needs a problem attempt.", 422)
            if inp.attempt.problem_id != step.problem_id:
                raise AppError(ErrorCode.VALIDATION_ERROR, "The attempt is for a different problem.", 422)
            recorded_attempt = ActivityService(self._s, self._clock).record_attempt(inp.attempt)
            attempt_id = recorded_attempt.id
            step.observation_type, step.observation_id = "ATTEMPT", recorded_attempt.id
            step.passed = inp.attempt.outcome == "PASS"
        else:
            step.reflection = inp.reflection
        step.status = "DONE"
        step.completed_at = _naive_now(self._clock)
        self._audit(
            row.id,
            "COMPLETE_LEARNING_STEP",
            {
                "position": position,
                "observation_type": step.observation_type,
                "observation_id": step.observation_id,
                "points": step.points,
                "passed": step.passed,
            },
        )
        self._finish_if_done(row)
        self._s.commit()
        return StepResultOut(session=self.session(row.id), completion=completion, attempt_id=attempt_id)

    def skip_step(self, session_id: int, position: int) -> SessionOut:
        row, step = self._active_step(session_id, position)
        step.status = "SKIPPED"
        step.completed_at = _naive_now(self._clock)
        self._audit(row.id, "SKIP_LEARNING_STEP", {"position": position})
        self._finish_if_done(row)
        self._s.commit()
        return self.session(row.id)

    def abandon(self, session_id: int) -> SessionOut:
        row = self._repo.session(session_id)
        if row is None:
            raise _not_found(f"Learning session {session_id}")
        if row.status != "ACTIVE":
            raise _invalid(f"Learning session {session_id} is {row.status}.")
        row.status, row.completed_at = "ABANDONED", _naive_now(self._clock)
        self._audit(row.id, "ABANDON_LEARNING_SESSION", {})
        self._s.commit()
        return self.session(row.id)

    def _finish_if_done(self, row: LearningSession) -> None:
        self._s.flush()
        steps = self._repo.steps(row.id)
        summary = summarize([StepState(s.position, s.status, s.points, s.passed) for s in steps])
        if summary.status != "COMPLETED":
            return
        row.status, row.outcome, row.completed_at = "COMPLETED", summary.outcome, _naive_now(self._clock)
        self._audit(row.id, "COMPLETE_LEARNING_SESSION", {"outcome": summary.outcome})
        if row.plan_item_id is None:
            return
        observed = [s for s in steps if s.observation_id is not None and s.observation_type]
        scored = [s for s in observed if s.passed is not None]
        last = (scored or observed)[-1] if observed else None
        item = self._s.get(PlanItemRow, row.plan_item_id)
        if last is not None and item is not None and item.status == "PENDING":
            from app.services.plan_service import PlanService

            assert last.observation_type is not None and last.observation_id is not None
            PlanService(self._s, self._clock).close_with_observation(
                item, last.observation_type, last.observation_id
            )
