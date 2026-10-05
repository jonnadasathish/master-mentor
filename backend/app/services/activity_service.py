"""Activity capture: record raw observations exactly as entered. No scoring, no derived state.

Every write is one transaction: the observation row(s) + one audit_log row.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.activity.rules import attempt_errors
from app.domain.activity.vocabulary import PERSONAL_SEED_VERSION
from app.domain.catalog.vocabulary import PRIMARY_MAPPING_BP
from app.domain.clock import Clock, local_date
from app.domain.learning.practice import AttemptFact, problem_state
from app.errors import AppError
from app.models import AuditLog, BaselineItem, Problem, ProblemAttempt, RevisionItemRow
from app.repositories.activity_repository import ActivityRepository, AttemptRow, ProblemStats
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.activity import (
    LastAttempt,
    PersonalProblemInput,
    ProblemAttemptInput,
    ProblemAttemptOut,
    ProblemOut,
    ProblemRef,
)
from app.schemas.envelope import ErrorCode

FALLBACK_TIMEZONE = "UTC"


def platform_url(problem: Problem) -> str | None:
    """The stored URL, or the platform's canonical page for a known platform."""
    if problem.url:
        return problem.url
    if problem.platform == "LEETCODE":
        return f"https://leetcode.com/problems/{problem.platform_key}/"
    return None


def attempt_fact(a: ProblemAttempt) -> AttemptFact:
    within = bool(
        a.timed
        and a.time_limit_seconds
        and a.time_seconds is not None
        and a.time_seconds <= a.time_limit_seconds
    )
    return AttemptFact(
        a.outcome, a.hints_used, a.solution_viewed, a.timed, within, a.explanation_score, a.complexity_correct
    )


def problem_key(problem: Problem) -> str:
    return f"{problem.platform}:{problem.platform_key}"


def problem_source(problem: Problem) -> str:
    return "PERSONAL" if problem.seed_version == PERSONAL_SEED_VERSION else "CATALOG"


def _validation(errors: list[tuple[str, str]]) -> AppError:
    return AppError(
        ErrorCode.VALIDATION_ERROR,
        "Request validation failed.",
        422,
        {"errors": [{"loc": ["body", field], "msg": msg, "type": "value_error"} for field, msg in errors]},
    )


def link_key_errors(
    session: Session, revision_item_key: str | None, battery_item_key: str | None, *, problem_id: int | None
) -> list[tuple[str, str]]:
    """A review links an existing revision item (PROBLEM: same problem); battery keys must exist."""
    errors: list[tuple[str, str]] = []
    if revision_item_key is not None:
        item = session.get(RevisionItemRow, revision_item_key)
        if item is None:
            errors.append(("revision_item_key", f"unknown revision item {revision_item_key!r}"))
        elif item.item_type == "PROBLEM" and (problem_id is None or item.subject_ref != str(problem_id)):
            errors.append(("revision_item_key", "a PROBLEM item is reviewed by an attempt on that problem"))
    if battery_item_key is not None and session.get(BaselineItem, battery_item_key) is None:
        errors.append(("battery_item_key", f"unknown baseline battery item {battery_item_key!r}"))
    return errors


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


class ActivityService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._repo = ActivityRepository(session)
        self._catalog = CatalogRepository(session)
        self._clock = clock

    # ------------------------------------------------------------------ problems
    def resolve_problem(self, ref: str) -> Problem:
        """``ref`` is a stable problem key "<PLATFORM>:<platform_key>" or a numeric problem id."""
        problem: Problem | None
        if ref.isdigit():
            problem = self._repo.problem(int(ref))
        elif ":" in ref:
            platform, key = ref.split(":", 1)
            problem = self._repo.problem_by_key(platform.upper(), key)
        else:
            problem = None
        if problem is None or not problem.active:
            raise AppError(ErrorCode.NOT_FOUND, f"Problem {ref!r} not found.", 404)
        return problem

    def _problem_out(self, stats: ProblemStats) -> ProblemOut:
        p = stats.problem
        mappings = self._catalog.problem_skill_mappings([p.id]).get(p.id, [])
        last = stats.last_attempt
        return ProblemOut(
            id=p.id,
            key=problem_key(p),
            platform=p.platform,
            platform_key=p.platform_key,
            title=p.title,
            url=platform_url(p),
            difficulty=p.difficulty,
            expected_minutes=p.expected_minutes,
            is_canonical=p.is_canonical,
            source=problem_source(p),
            skills=[
                {"skill": k, "mapping_weight_bp": w, "primary": w == PRIMARY_MAPPING_BP} for k, w in mappings
            ],
            attempt_count=stats.attempt_count,
            practice_state=problem_state([attempt_fact(a) for a in stats.attempts]),
            guide=p.guide_json,
            last_attempt=LastAttempt(
                id=last.id, attempted_at=last.attempted_at.replace(tzinfo=UTC), outcome=last.outcome
            )
            if last
            else None,
        )

    def list_problems(
        self, *, query: str | None, difficulty: str | None, skill: str | None, source: str | None
    ) -> list[ProblemOut]:
        if skill is not None and self._catalog.skill(skill) is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Skill {skill!r} not found.", 404)
        rows = self._repo.problems_with_stats(
            query=query, difficulty=difficulty, skill_key=skill, source=source
        )
        return [self._problem_out(row) for row in rows]

    def get_problem(self, ref: str) -> ProblemOut:
        problem = self.resolve_problem(ref)
        return self._problem_out(self._repo.problems_with_stats(problem_id=problem.id)[0])

    def create_personal_problem(self, payload: PersonalProblemInput) -> ProblemOut:
        keys = [s.skill for s in payload.skills]
        errors: list[tuple[str, str]] = []
        if sum(1 for s in payload.skills if s.mapping_weight_bp == PRIMARY_MAPPING_BP) != 1:
            errors.append(("skills", "exactly one skill must be primary (mapping_weight_bp 10000)"))
        if len(set(keys)) != len(keys):
            errors.append(("skills", "each skill may appear only once"))
        skill_ids = self._repo.active_skill_ids(keys)
        errors.extend(("skills", f"unknown or inactive skill {k!r}") for k in keys if k not in skill_ids)
        if errors:
            raise _validation(errors)
        existing = self._repo.problem_by_key(payload.platform, payload.platform_key)
        if existing is not None:
            raise AppError(
                ErrorCode.CONFLICT,
                f"Problem {payload.platform}:{payload.platform_key} already exists.",
                409,
                {"problem_id": existing.id, "source": problem_source(existing)},
            )
        now = self._clock.now_utc()
        problem = Problem(
            id=self._repo.next_personal_problem_id(),
            platform=payload.platform,
            platform_key=payload.platform_key,
            title=payload.title,
            url=payload.url,
            difficulty=payload.difficulty,
            expected_minutes=payload.expected_minutes,
            is_canonical=False,
            active=True,
            seed_version=PERSONAL_SEED_VERSION,
        )
        self._repo.add_problem(problem, [(skill_ids[s.skill], s.mapping_weight_bp) for s in payload.skills])
        self._audit(
            now, "problem", str(problem.id), "CREATE_PERSONAL_PROBLEM", payload.model_dump(mode="json")
        )
        self._commit()
        return self.get_problem(str(problem.id))

    # ------------------------------------------------------------------ attempts
    def _build_attempt(self, payload: ProblemAttemptInput, *, supersedes_id: int | None) -> ProblemAttempt:
        problem = self._repo.problem(payload.problem_id)
        if problem is None or not problem.active:
            raise AppError(ErrorCode.NOT_FOUND, f"Problem {payload.problem_id} not found.", 404)
        now = self._clock.now_utc()
        attempted_at = payload.attempted_at or now
        errors = attempt_errors(
            attempted_at=attempted_at,
            now_utc=now,
            timed=payload.timed,
            time_seconds=payload.time_seconds,
            time_limit_seconds=payload.time_limit_seconds,
            mistakes=tuple(payload.mistakes),
        )
        link_errors = link_key_errors(
            self._s, payload.revision_item_key, payload.battery_item_key, problem_id=problem.id
        )
        if errors or link_errors:
            raise _validation([(e.field, e.message) for e in errors] + link_errors)
        rubric = payload.execution_rubric.model_dump(exclude_none=True) if payload.execution_rubric else None
        return ProblemAttempt(
            problem_id=problem.id,
            attempted_on=local_date(attempted_at, self._repo.timezone() or FALLBACK_TIMEZONE),
            attempted_at=_naive_utc(attempted_at),
            mode=payload.mode,
            outcome=payload.outcome,
            seen_elsewhere=payload.seen_elsewhere,
            hints_used=payload.hints_used,
            solution_viewed=payload.solution_viewed,
            pattern_identified=payload.pattern_identified,
            timed=payload.timed,
            time_limit_seconds=payload.time_limit_seconds,
            time_seconds=payload.time_seconds,
            explanation_score=payload.explanation_score,
            complexity_correct=payload.complexity_correct,
            followup_solved=payload.followup_solved,
            execution_rubric_json=rubric or None,
            self_rating_before=payload.self_rating_before,
            self_rating_after=payload.self_rating_after,
            notes=payload.notes,
            revision_item_key=payload.revision_item_key,
            battery_item_key=payload.battery_item_key,
            client_request_id=payload.client_request_id,
            supersedes_id=supersedes_id,
            created_at=_naive_utc(now),
        )

    def record_attempt(
        self, payload: ProblemAttemptInput, *, plan_item_id: int | None = None
    ) -> ProblemAttemptOut:
        if payload.client_request_id and (
            dup := self._repo.attempt_by_client_request(payload.client_request_id)
        ):
            raise AppError(
                ErrorCode.CONFLICT, "This attempt was already recorded.", 409, {"attempt_id": dup.id}
            )
        attempt = self._build_attempt(payload, supersedes_id=None)
        attempt.plan_item_id = plan_item_id
        self._repo.add_attempt(attempt, payload.mistakes)
        self._audit(
            attempt.created_at,
            "problem_attempt",
            str(attempt.id),
            "CREATE_PROBLEM_ATTEMPT",
            payload.model_dump(mode="json"),
        )
        self._commit()
        return self.get_attempt(attempt.id)

    def correct_attempt(self, attempt_id: int, payload: ProblemAttemptInput) -> ProblemAttemptOut:
        """Append a corrected version; the original row is never modified."""
        original = self._repo.attempts(attempt_id=attempt_id, include_superseded=True)
        if not original:
            raise AppError(ErrorCode.NOT_FOUND, f"Attempt {attempt_id} not found.", 404)
        if original[0].superseded_by_id is not None:
            raise AppError(
                ErrorCode.INVALID_STATE,
                "This attempt was already corrected; correct its latest version instead.",
                409,
                {"latest_attempt_id": self._latest_version(attempt_id)},
            )
        attempt = self._build_attempt(payload, supersedes_id=attempt_id)
        self._repo.add_attempt(attempt, payload.mistakes)
        self._audit(
            attempt.created_at,
            "problem_attempt",
            str(attempt.id),
            "CORRECT_PROBLEM_ATTEMPT",
            {"supersedes_id": attempt_id, "input": payload.model_dump(mode="json")},
        )
        self._commit()
        return self.get_attempt(attempt.id)

    def _latest_version(self, attempt_id: int) -> int:
        current = attempt_id
        while (nxt := self._repo.successor_id(current)) is not None:
            current = nxt
        return current

    def get_attempt(self, attempt_id: int) -> ProblemAttemptOut:
        rows = self._repo.attempts(attempt_id=attempt_id, include_superseded=True)
        if not rows:
            raise AppError(ErrorCode.NOT_FOUND, f"Attempt {attempt_id} not found.", 404)
        return _attempt_out(rows[0])

    def list_attempts(self, **filters: Any) -> list[ProblemAttemptOut]:
        if filters.get("skill_key") is not None and self._catalog.skill(filters["skill_key"]) is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Skill {filters['skill_key']!r} not found.", 404)
        return [_attempt_out(row) for row in self._repo.attempts(**filters)]

    # ------------------------------------------------------------------ helpers
    def _audit(
        self, at: datetime, entity_type: str, entity_id: str, action: str, payload: dict[str, Any]
    ) -> None:
        at_utc = at if at.tzinfo is None else _naive_utc(at)
        self._s.add(
            AuditLog(
                at=at_utc, entity_type=entity_type, entity_id=entity_id, action=action, payload_json=payload
            )
        )

    def _commit(self) -> None:
        try:
            self._s.commit()
        except IntegrityError as exc:
            self._s.rollback()
            raise AppError(ErrorCode.CONFLICT, "The record conflicts with existing data.", 409) from exc


def _attempt_out(row: AttemptRow) -> ProblemAttemptOut:
    a, p = row.attempt, row.problem
    return ProblemAttemptOut(
        id=a.id,
        problem=ProblemRef(
            id=p.id,
            key=problem_key(p),
            title=p.title,
            difficulty=p.difficulty,
            source=problem_source(p),
        ),
        attempted_at=a.attempted_at.replace(tzinfo=UTC),
        attempted_on=a.attempted_on,
        mode=a.mode,
        outcome=a.outcome,
        seen_elsewhere=a.seen_elsewhere,
        hints_used=a.hints_used,
        solution_viewed=a.solution_viewed,
        pattern_identified=a.pattern_identified,
        timed=a.timed,
        time_limit_seconds=a.time_limit_seconds,
        time_seconds=a.time_seconds,
        explanation_score=a.explanation_score,
        complexity_correct=a.complexity_correct,
        followup_solved=a.followup_solved,
        execution_rubric=a.execution_rubric_json,
        mistakes=list(row.mistakes),
        self_rating_before=a.self_rating_before,
        self_rating_after=a.self_rating_after,
        notes=a.notes,
        revision_item_key=a.revision_item_key,
        battery_item_key=a.battery_item_key,
        supersedes_id=a.supersedes_id,
        superseded_by_id=row.superseded_by_id,
        is_current=row.superseded_by_id is None,
        created_at=a.created_at.replace(tzinfo=UTC),
        skill_mapping_bp=row.skill_mapping_bp,
    )


def parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _validation([(field, "must be a date YYYY-MM-DD")]) from exc
