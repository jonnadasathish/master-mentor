"""Mock interviews and final simulations (raw; corrections supersede) + the Mocks page summary."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import with_effects
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.envelope import Meta, success
from app.schemas.mock import MockInput
from app.services.mock_service import MockService
from app.services.skill_service import SkillService

router = APIRouter(tags=["mocks"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


@router.post("/mocks", status_code=201)
def record_mock(session: DbSession, clock: ClockDep, payload: MockInput) -> dict[str, Any]:
    """Each round skill emits L7 evidence; ``is_weakness`` rows create MOCK_WEAKNESS revision items."""
    return with_effects(session, clock, MockService(session, clock).record(payload))


@router.get("/mocks")
def list_mocks(
    session: DbSession,
    clock: ClockDep,
    include_superseded: bool = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    items = MockService(session, clock).list_mocks(include_superseded=include_superseded, limit=limit)
    return success([m.model_dump(mode="json") for m in items], Meta(count=len(items)))


@router.get("/mocks/summary")
def mocks_summary(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    skills = SkillService(session, clock)
    run = skills.ensure_current_run()
    return success(MockService(session, clock).summary(), skills.meta(run))


@router.get("/mocks/{mock_id}")
def get_mock(session: DbSession, clock: ClockDep, mock_id: int) -> dict[str, Any]:
    return success(MockService(session, clock).get(mock_id))


@router.post("/mocks/{mock_id}/corrections", status_code=201)
def correct_mock(session: DbSession, clock: ClockDep, mock_id: int, payload: MockInput) -> dict[str, Any]:
    corrected = MockService(session, clock).correct(mock_id, payload)
    return with_effects(session, clock, corrected, MentorRunTrigger.CORRECTION)
