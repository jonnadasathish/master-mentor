"""Assessment capture API (quizzes, explanations, designs, rehearsals, study, self-assessment sweep)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import with_effects
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.assessment import AssessmentInput, AssessmentKind, SelfAssessmentSweepInput
from app.schemas.envelope import Meta, success
from app.services.activity_service import parse_date
from app.services.assessment_service import AssessmentService

router = APIRouter(tags=["assessments"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


@router.post("/assessments", status_code=201)
def record_assessment(session: DbSession, clock: ClockDep, payload: AssessmentInput) -> dict[str, Any]:
    return with_effects(session, clock, AssessmentService(session, clock).record(payload))


@router.post("/assessments/self-assessment-sweep", status_code=201)
def self_assessment_sweep(
    session: DbSession, clock: ClockDep, payload: SelfAssessmentSweepInput
) -> dict[str, Any]:
    """Battery item M0-B01: one SELF_ASSESSMENT per skill. NONE = declared unknown (score 0, LOW)."""
    return with_effects(session, clock, AssessmentService(session, clock).sweep(payload))


@router.get("/assessments")
def list_assessments(
    session: DbSession,
    clock: ClockDep,
    kind: AssessmentKind | None = None,
    skill: str | None = None,
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
    include_superseded: bool = False,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    items = AssessmentService(session, clock).list_assessments(
        kind=kind,
        skill_key=skill,
        date_from=parse_date(date_from, "from"),
        date_to=parse_date(date_to, "to"),
        include_superseded=include_superseded,
        limit=limit,
        offset=offset,
    )
    return success([i.model_dump(mode="json") for i in items], Meta(count=len(items)))


@router.get("/assessments/{assessment_id}")
def get_assessment(session: DbSession, clock: ClockDep, assessment_id: int) -> dict[str, Any]:
    return success(AssessmentService(session, clock).get(assessment_id))


@router.post("/assessments/{assessment_id}/corrections", status_code=201)
def correct_assessment(
    session: DbSession, clock: ClockDep, assessment_id: int, payload: AssessmentInput
) -> dict[str, Any]:
    corrected = AssessmentService(session, clock).correct(assessment_id, payload)
    return with_effects(session, clock, corrected, MentorRunTrigger.CORRECTION)
