"""Learning layer API (API_SPEC §11): curriculum, content, completion, skill learning, sessions, coverage.

Completions are observation writes: they return the write envelope with the effects of the mentor run.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import run_then
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.envelope import Meta, success
from app.schemas.learning import CompletionIn, SessionStartIn, StepCompleteIn, StepResultOut
from app.services.learning_service import LearningService
from app.services.skill_service import SkillService

router = APIRouter(tags=["learning"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def get_learning(session: DbSession, clock: ClockDep) -> LearningService:
    return LearningService(session, clock)


Learning = Annotated[LearningService, Depends(get_learning)]


def _fresh(session: Session, clock: Clock) -> Meta:
    """Derived read models (skill state, gaps) come from today's run; make sure it exists."""
    skills = SkillService(session, clock)
    return skills.meta(skills.ensure_current_run())


@router.get("/learning/curriculum")
def curriculum(learning: Learning, session: DbSession, clock: ClockDep) -> dict[str, Any]:
    meta = _fresh(session, clock)
    tracks = learning.curriculum()
    return success(
        [t.model_dump(mode="json") for t in tracks], meta.model_copy(update={"count": len(tracks)})
    )


@router.get("/learning/tracks/{track_key}")
def track(learning: Learning, session: DbSession, clock: ClockDep, track_key: str) -> dict[str, Any]:
    meta = _fresh(session, clock)
    return success(learning.track(track_key), meta)


@router.get("/learning/content/{content_key}")
def content(learning: Learning, content_key: str) -> dict[str, Any]:
    return success(learning.content(content_key))


@router.post("/learning/content/{content_key}/complete", status_code=201)
def complete(
    learning: Learning, session: DbSession, clock: ClockDep, content_key: str, payload: CompletionIn
) -> dict[str, Any]:
    """Grades the completion and records the existing observation it stands for (LEARNING_ENGINE §4)."""
    out = learning.complete(content_key, payload)
    return run_then(session, clock, lambda: out, MentorRunTrigger.OBSERVATION)


@router.get("/skills/{skill_key}/learning")
def skill_learning(learning: Learning, session: DbSession, clock: ClockDep, skill_key: str) -> dict[str, Any]:
    meta = _fresh(session, clock)
    return success(learning.skill_learning(skill_key), meta)


@router.get("/learning/coverage")
def coverage(learning: Learning) -> dict[str, Any]:
    return success(learning.coverage())


@router.get("/learning/mock-kits")
def mock_kits(learning: Learning, session: DbSession, clock: ClockDep) -> dict[str, Any]:
    meta = _fresh(session, clock)
    kits = learning.mock_kits()
    return success([k.model_dump(mode="json") for k in kits], meta.model_copy(update={"count": len(kits)}))


@router.get("/learning/sessions")
def sessions(
    learning: Learning, status: Literal["ACTIVE", "COMPLETED", "ABANDONED"] | None = None
) -> dict[str, Any]:
    items = learning.sessions(status)
    return success([s.model_dump(mode="json") for s in items], Meta(count=len(items)))


@router.post("/learning/sessions", status_code=201)
def start_session(
    learning: Learning, session: DbSession, clock: ClockDep, payload: SessionStartIn
) -> dict[str, Any]:
    """Starts a session for the skill, or returns the one already active (resume)."""
    _fresh(session, clock)
    return success(learning.start_session(payload))


@router.get("/learning/sessions/{session_id}")
def get_session_detail(learning: Learning, session_id: int) -> dict[str, Any]:
    return success(learning.session(session_id))


@router.post("/learning/sessions/{session_id}/steps/{position}/complete")
def complete_step(
    learning: Learning,
    session: DbSession,
    clock: ClockDep,
    session_id: int,
    position: int,
    payload: StepCompleteIn,
) -> dict[str, Any]:
    result = learning.complete_step(session_id, position, payload)
    if result.completion is None and result.attempt_id is None:
        return success(result)  # a reflection records no observation

    def fetch() -> StepResultOut:  # read the session after the run so "after" shows the new state
        fresh = LearningService(session, clock).session(session_id)
        return StepResultOut(session=fresh, completion=result.completion, attempt_id=result.attempt_id)

    return run_then(session, clock, fetch, MentorRunTrigger.OBSERVATION)


@router.post("/learning/sessions/{session_id}/steps/{position}/skip")
def skip_step(learning: Learning, session_id: int, position: int) -> dict[str, Any]:
    return success(learning.skip_step(session_id, position))


@router.post("/learning/sessions/{session_id}/abandon")
def abandon(learning: Learning, session_id: int) -> dict[str, Any]:
    return success(learning.abandon(session_id))
