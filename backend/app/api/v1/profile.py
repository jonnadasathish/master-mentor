"""Settings and versioned goals. Every change is audited and followed by a mentor run (trigger GOAL)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import with_effects
from app.config import get_settings
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.envelope import Meta, success
from app.schemas.profile import GoalInput, GoalPatch, SettingsPatch
from app.services.profile_service import ProfileService

router = APIRouter(tags=["profile"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def service(session: Session, clock: Clock) -> ProfileService:
    return ProfileService(session, clock, get_settings().ruleset_version)


@router.get("/settings")
def get_settings_(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    return success(service(session, clock).settings())


@router.patch("/settings")
def patch_settings(session: DbSession, clock: ClockDep, payload: SettingsPatch) -> dict[str, Any]:
    """Timezone changes move every future local date; past observations keep their stored local date."""
    updated = service(session, clock).update_settings(payload)
    return with_effects(session, clock, updated, MentorRunTrigger.GOAL)


@router.get("/goals/active")
def active_goal(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    return success(service(session, clock).active_goal())


@router.get("/goals/history")
def goal_history(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    items = service(session, clock).history()
    return success([g.model_dump(mode="json") for g in items], Meta(count=len(items)))


@router.post("/goals", status_code=201)
def create_goal(session: DbSession, clock: ClockDep, payload: GoalInput) -> dict[str, Any]:
    """New goal version valid from today; closes the previous version (audited)."""
    return with_effects(session, clock, service(session, clock).create_goal(payload), MentorRunTrigger.GOAL)


@router.patch("/goals/active")
def patch_goal(session: DbSession, clock: ClockDep, payload: GoalPatch) -> dict[str, Any]:
    """Change target date / weekday budgets / profile: inserts a new version valid from today (audited)."""
    return with_effects(session, clock, service(session, clock).patch_goal(payload), MentorRunTrigger.GOAL)
