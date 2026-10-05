"""Readiness (READINESS_MODEL §10): today's gate view and the daily snapshot history."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.errors import AppError
from app.infrastructure.db import get_session
from app.models import ReadinessSnapshot
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.envelope import ErrorCode, Meta, success
from app.services.activity_service import parse_date
from app.services.skill_service import SkillService

router = APIRouter(tags=["readiness"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
HISTORY_DEFAULT_DAYS = 90


def snapshot_json(s: ReadinessSnapshot) -> dict[str, Any]:
    return {
        "as_of_date": s.snapshot_date.isoformat(),
        "run_id": s.run_id,
        "ruleset_version": s.ruleset_version,
        "state": s.state,
        "simulation_eligible": s.simulation_eligible,
        "lapsed": s.lapsed,
        "weighted_score": s.weighted_score,
        "limiting_component": s.limiting_component,
        "components": s.components_json,
        "gates": s.gates_json,
        "blockers": s.blockers_json,
        "all_failing": s.all_failing_json,
    }


@router.get("/readiness")
def readiness(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    """State is decided by gates only; ``weighted_score`` is for trend display."""
    skills = SkillService(session, clock)
    run = skills.ensure_current_run()
    snap = EvidenceRepository(session).readiness_snapshot(run.as_of_date)
    if snap is None:
        raise AppError(ErrorCode.INVALID_STATE, "No readiness snapshot yet; load the catalog first.", 409)
    return success(snapshot_json(snap), skills.meta(run))


@router.get("/readiness/history")
def readiness_history(
    session: DbSession,
    clock: ClockDep,
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
) -> dict[str, Any]:
    """Daily snapshots (state, weighted score, components) in date order."""
    skills = SkillService(session, clock)
    run = skills.ensure_current_run()
    end = parse_date(date_to, "to") or run.as_of_date
    start = parse_date(date_from, "from") or end - timedelta(days=HISTORY_DEFAULT_DAYS)
    rows = EvidenceRepository(session).readiness_history(start, end)
    items = [
        {
            "date": r.snapshot_date.isoformat(),
            "state": r.state,
            "weighted_score": r.weighted_score,
            "limiting_component": r.limiting_component,
            "components": {str(c["key"]): c["score"] for c in r.components_json},
            "blockers": len(r.blockers_json),
        }
        for r in rows
    ]
    return success(
        items,
        Meta(as_of_date=run.as_of_date, ruleset_version=run.ruleset_version, run_id=run.id, count=len(items)),
    )
