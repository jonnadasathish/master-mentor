"""Weekly reviews: generated lazily after the week ends; reflection is audited free text."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.schemas.envelope import Meta, success
from app.schemas.review import ReflectionIn
from app.services.activity_service import parse_date
from app.services.review_service import ReviewService

router = APIRouter(tags=["review"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def _week(value: str):  # type: ignore[no-untyped-def]
    day = parse_date(value, "week_start")
    assert day is not None
    return day


@router.get("/weekly-reviews")
def list_reviews(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    items = ReviewService(session, clock).list_reviews()
    return success([i.model_dump(mode="json") for i in items], Meta(count=len(items)))


@router.get("/weekly-reviews/latest")
def latest(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    """The last completed Monday-Sunday week; generated on first request."""
    return success(ReviewService(session, clock).latest())


@router.get("/weekly-reviews/{week_start}")
def get_review(session: DbSession, clock: ClockDep, week_start: str) -> dict[str, Any]:
    return success(ReviewService(session, clock).get(_week(week_start)))


@router.post("/weekly-reviews/{week_start}/reflection")
def reflect(session: DbSession, clock: ClockDep, week_start: str, payload: ReflectionIn) -> dict[str, Any]:
    return success(ReviewService(session, clock).reflect(_week(week_start), payload))
