"""Activity capture API: problems (catalog + personal) and raw problem attempts (+ write effects, Slice 4)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import with_effects
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.activity import PersonalProblemInput, ProblemAttemptInput
from app.schemas.envelope import Meta, success
from app.services.activity_service import ActivityService, parse_date

router = APIRouter(tags=["activity"])


def get_activity(
    session: Annotated[Session, Depends(get_session)], clock: Annotated[Clock, Depends(get_clock)]
) -> ActivityService:
    return ActivityService(session, clock)


Activity = Annotated[ActivityService, Depends(get_activity)]
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def _list(items: list[Any]) -> dict[str, Any]:
    return success([i.model_dump(mode="json") for i in items], Meta(count=len(items)))


# ---------------------------------------------------------------------------------------- problems


@router.get("/problems")
def list_problems(
    activity: Activity,
    q: Annotated[str | None, Query(max_length=100)] = None,
    difficulty: Literal["EASY", "MEDIUM", "HARD"] | None = None,
    skill: str | None = None,
    source: Literal["CATALOG", "PERSONAL"] | None = None,
) -> dict[str, Any]:
    """Active catalog + personal problems with the user's attempt count and last attempt."""
    return _list(activity.list_problems(query=q, difficulty=difficulty, skill=skill, source=source))


@router.post("/problems", status_code=201)
def create_personal_problem(activity: Activity, payload: PersonalProblemInput) -> dict[str, Any]:
    """Add a personal problem (never touches the seeded catalog)."""
    return success(activity.create_personal_problem(payload))


@router.get("/problems/{problem_ref}")
def get_problem(activity: Activity, problem_ref: str) -> dict[str, Any]:
    """``problem_ref`` = stable key "<PLATFORM>:<platform_key>" (e.g. LEETCODE:two-sum) or numeric id."""
    return success(activity.get_problem(problem_ref))


@router.get("/problems/{problem_ref}/attempts")
def problem_attempts(
    activity: Activity, problem_ref: str, include_superseded: bool = False
) -> dict[str, Any]:
    """One problem's history in chronological order."""
    problem = activity.resolve_problem(problem_ref)
    return _list(
        activity.list_attempts(
            problem_id=problem.id, include_superseded=include_superseded, ascending=True, limit=1000
        )
    )


# ---------------------------------------------------------------------------------------- attempts


@router.post("/problem-attempts", status_code=201)
def record_attempt(
    activity: Activity, session: DbSession, clock: ClockDep, payload: ProblemAttemptInput
) -> dict[str, Any]:
    """Record a raw attempt exactly as observed; ``effects`` carries the resulting skill deltas."""
    return with_effects(session, clock, activity.record_attempt(payload))


@router.get("/problem-attempts")
def list_attempts(
    activity: Activity,
    skill: str | None = None,
    problem: str | None = None,
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
    outcome: Literal["PASS", "PARTIAL", "FAIL"] | None = None,
    include_superseded: bool = False,
    order: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Recent attempts (newest first) or filtered by skill / problem / local date range / outcome."""
    problem_id = activity.resolve_problem(problem).id if problem is not None else None
    return _list(
        activity.list_attempts(
            skill_key=skill,
            problem_id=problem_id,
            date_from=parse_date(date_from, "from"),
            date_to=parse_date(date_to, "to"),
            outcome=outcome,
            include_superseded=include_superseded,
            ascending=order == "asc",
            limit=limit,
            offset=offset,
        )
    )


@router.get("/problem-attempts/{attempt_id}")
def get_attempt(activity: Activity, attempt_id: int) -> dict[str, Any]:
    return success(activity.get_attempt(attempt_id))


@router.post("/problem-attempts/{attempt_id}/corrections", status_code=201)
def correct_attempt(
    activity: Activity, session: DbSession, clock: ClockDep, attempt_id: int, payload: ProblemAttemptInput
) -> dict[str, Any]:
    """Append a corrected version; the original stays unchanged and links to its correction."""
    return with_effects(
        session, clock, activity.correct_attempt(attempt_id, payload), MentorRunTrigger.CORRECTION
    )
