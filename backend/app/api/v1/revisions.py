"""Revision items (REVISION_ENGINE): bucketed list with backlog/cap, manual suspend/resume.

A review is recorded by posting an attempt/assessment with ``revision_item_key``; the run moves the schedule.
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
from app.schemas.envelope import success
from app.services.revision_service import RevisionService

router = APIRouter(tags=["revision"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
Bucket = Literal["overdue", "due", "upcoming", "maintenance", "suspended", "graduated"]


@router.get("/revisions")
def list_revisions(session: DbSession, clock: ClockDep, bucket: Bucket | None = None) -> dict[str, Any]:
    """``data = {backlog_minutes, cap_minutes, triage_threshold_minutes, counts, items[]}``, due order."""
    service = RevisionService(session, clock)
    skills = service.skills
    run = skills.ensure_current_run()
    listing = service.listing(bucket)
    return success(listing, skills.meta(run, len(listing.items)))


def _act(session: Session, clock: Clock, item_key: str, action: str) -> dict[str, Any]:
    service = RevisionService(session, clock)
    service.manual_action(item_key, action)
    return run_then(
        session, clock, lambda: RevisionService(session, clock).item(item_key), MentorRunTrigger.PLAN
    )


@router.post("/revisions/{item_key}/suspend")
def suspend(session: DbSession, clock: ClockDep, item_key: str) -> dict[str, Any]:
    """Manual suspend (audited action row, replayed by every rebuild)."""
    return _act(session, clock, item_key, "SUSPEND")


@router.post("/revisions/{item_key}/resume")
def resume(session: DbSession, clock: ClockDep, item_key: str) -> dict[str, Any]:
    """Manual resume: due today (audited action row)."""
    return _act(session, clock, item_key, "RESUME")
