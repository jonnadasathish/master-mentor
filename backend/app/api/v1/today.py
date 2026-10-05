"""Today page and plan actions (API_SPEC "Today and plan"). The plan is frozen at the first GET /today."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import run_then
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.envelope import Meta, success
from app.schemas.plan import CompleteIn, ItemActionOut, SkipIn
from app.services.activity_service import parse_date
from app.services.plan_service import PlanService

router = APIRouter(tags=["today"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def _meta(today: Any) -> Meta:
    return Meta(
        as_of_date=today.plan_date, ruleset_version=today.plan.ruleset_version, run_id=today.plan.run_id
    )


@router.get("/today")
def get_today(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    """Readiness summary, calibration, top gaps, frozen plan, stop list, message, revision counts."""
    today = PlanService(session, clock).today()
    return success(today, _meta(today))


@router.get("/today/week")
def get_week(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    """Week-to-date practice context for the Today page (read-only; creates no plan and runs no engine)."""
    week = PlanService(session, clock).week()
    return success(week, Meta(as_of_date=week.plan_date))


@router.post("/plan/today/regenerate")
def regenerate(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    """Keeps DONE/SKIPPED items, discards PENDING ones and repacks the remaining budget (audited)."""
    service = PlanService(session, clock)
    service.regenerate()
    today = service.today()
    return success(today, _meta(today))


@router.post("/plan/items/{item_id}/start")
def start(session: DbSession, clock: ClockDep, item_id: int) -> dict[str, Any]:
    service = PlanService(session, clock)
    return success(service.item_out(service.start(item_id)))


@router.post("/plan/items/{item_id}/complete")
def complete(session: DbSession, clock: ClockDep, item_id: int, payload: CompleteIn) -> dict[str, Any]:
    """``{observation: {type, body}}`` (body = the attempt/assessment fields) or ``{no_evidence: true}``."""
    service = PlanService(session, clock)
    obs = (payload.observation.type, payload.observation.body) if payload.observation else None
    item, recorded = service.complete(item_id, obs, payload.no_evidence)
    return run_then(
        session,
        clock,
        lambda: ItemActionOut(item=PlanService(session, clock).item_out(item), observation=recorded),
        MentorRunTrigger.OBSERVATION,
    )


@router.post("/plan/items/{item_id}/skip")
def skip(session: DbSession, clock: ClockDep, item_id: int, payload: SkipIn) -> dict[str, Any]:
    """A skipped revision is MISSED: no schedule change."""
    service = PlanService(session, clock)
    return success(service.item_out(service.skip(item_id, payload.skip_reason)))


@router.post("/plan/items/{item_id}/defer")
def defer(session: DbSession, clock: ClockDep, item_id: int) -> dict[str, Any]:
    """Re-offered tomorrow with +5, once."""
    service = PlanService(session, clock)
    return success(service.item_out(service.defer(item_id)))


@router.get("/plan/{plan_date}")
def plan_on(session: DbSession, clock: ClockDep, plan_date: str) -> dict[str, Any]:
    """Historical plan (read-only)."""
    day: date | None = parse_date(plan_date, "plan_date")
    assert day is not None
    plan = PlanService(session, clock).plan_for(day)
    return success(
        plan, Meta(as_of_date=plan.plan_date, ruleset_version=plan.ruleset_version, run_id=plan.run_id)
    )
