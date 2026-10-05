"""Ranked gaps (GAP_ENGINE §10-§11) from the current mentor run."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.schemas.envelope import success
from app.services.gap_service import GapService

router = APIRouter(tags=["gaps"])


def get_gaps(
    session: Annotated[Session, Depends(get_session)], clock: Annotated[Clock, Depends(get_clock)]
) -> GapService:
    return GapService(session, clock)


Gaps = Annotated[GapService, Depends(get_gaps)]
Status = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "UNASSESSED", "BLOCKED", "PARKED"]


@router.get("/gaps")
def list_gaps(
    gaps: Gaps,
    status: Status | None = None,
    component: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
) -> dict[str, Any]:
    """``data = {phase, weeks_left, infeasible_components, calibration_mode, gaps[]}`` ranked."""
    run = gaps.ensure_current_run()
    report = gaps.report(status=status, component=component, limit=limit)
    return success(report, gaps.meta(run, len(report.gaps)))


@router.get("/gaps/{skill_key}")
def gap_detail(gaps: Gaps, skill_key: str) -> dict[str, Any]:
    """One gap with metrics and the evidence rows behind each reason code."""
    run = gaps.ensure_current_run()
    return success(gaps.detail(skill_key), gaps.meta(run))
