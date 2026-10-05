"""Skill state read models and baseline/calibration status (derived; carry meta.run_id)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.schemas.envelope import success
from app.services.roadmap_service import RoadmapService
from app.services.skill_service import SkillService

router = APIRouter(tags=["skills"])


def get_skills(
    session: Annotated[Session, Depends(get_session)], clock: Annotated[Clock, Depends(get_clock)]
) -> SkillService:
    return SkillService(session, clock)


Skills = Annotated[SkillService, Depends(get_skills)]
Label = Literal["UNASSESSED", "WEAK", "DEVELOPING", "WORKING", "STRONG", "INTERVIEW_GRADE"]


@router.get("/skills")
def list_skills(
    skills: Skills,
    component: str | None = None,
    group: str | None = None,
    tier: Literal["T1", "T2", "T3", "T4"] | None = None,
    label: Label | None = None,
) -> dict[str, Any]:
    run = skills.ensure_current_run()
    items = skills.list_skills(component=component, group=group, tier=tier, label=label)
    return success([i.model_dump(mode="json") for i in items], skills.meta(run, len(items)))


@router.get("/skills/{skill_key}")
def skill_detail(skills: Skills, skill_key: str) -> dict[str, Any]:
    run = skills.ensure_current_run()
    return success(skills.detail(skill_key), skills.meta(run))


@router.get("/roadmap")
def roadmap(
    session: Annotated[Session, Depends(get_session)], clock: Annotated[Clock, Depends(get_clock)]
) -> dict[str, Any]:
    """Tracks x milestones with completion, current milestone per track, baseline battery progress."""
    skills = SkillService(session, clock)
    run = skills.ensure_current_run()
    return success(RoadmapService(session, clock).roadmap(), skills.meta(run))


@router.get("/baseline")
def baseline(skills: Skills) -> dict[str, Any]:
    """Baseline battery progress + Calibration Mode (MENTOR_ENGINE.md §2)."""
    run = skills.ensure_current_run()
    return success(skills.baseline(), skills.meta(run))
