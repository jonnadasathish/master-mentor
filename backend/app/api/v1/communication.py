"""Communication API (D-087): the read-only Communication Readiness view and a transcript preview.

Speaking practice is recorded through the ordinary learning completion
(``POST /learning/content/{key}/complete`` with ``speech``): the same evidence path as every other practice.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.schemas.communication import SpeechPreviewIn
from app.schemas.envelope import Meta, success
from app.services.communication_service import CommunicationService
from app.services.skill_service import SkillService

router = APIRouter(tags=["communication"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def _service(session: DbSession, clock: ClockDep) -> CommunicationService:
    return CommunicationService(session, clock)


Communication = Annotated[CommunicationService, Depends(_service)]


@router.get("/communication/readiness")
def readiness(service: Communication, session: DbSession, clock: ClockDep) -> dict[str, Any]:
    skills = SkillService(session, clock)
    meta: Meta = skills.meta(skills.ensure_current_run())
    return success(service.readiness().model_dump(mode="json"), meta)


@router.get("/communication/history")
def history(service: Communication, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict[str, Any]:
    """Recent speaking practices (counts only, no transcripts), newest first."""
    out = service.history(limit)
    return success(out.model_dump(mode="json"), Meta(count=len(out.rows)))


@router.post("/communication/preview")
def preview(service: Communication, payload: SpeechPreviewIn) -> dict[str, Any]:
    """Measure a transcript before submitting it. Nothing is stored."""
    return success(service.preview(payload).model_dump(mode="json"))
