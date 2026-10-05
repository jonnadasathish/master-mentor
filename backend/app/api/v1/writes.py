"""Shared post-write step: every observation write is followed by one synchronous mentor run."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.models.system import MentorRunTrigger
from app.schemas.envelope import Meta, write_success
from app.services.mentor_service import MentorService


def with_effects(
    session: Session,
    clock: Clock,
    data: BaseModel | list[Any],
    trigger: MentorRunTrigger = MentorRunTrigger.OBSERVATION,
) -> dict[str, Any]:
    """The observation is already committed; the run is derived (rebuildable) and committed separately."""
    result = MentorService(session, clock).recalculate(trigger)
    meta = Meta(
        as_of_date=result.as_of_date,
        ruleset_version=result.ruleset_version,
        seed_version=result.seed_version,
        run_id=result.run_id,
        count=len(data) if isinstance(data, list) else None,
    )
    payload: Any = [d.model_dump(mode="json") for d in data] if isinstance(data, list) else data
    return write_success(payload, meta, result.effects())


def run_then(
    session: Session, clock: Clock, fetch: Callable[[], BaseModel], trigger: MentorRunTrigger
) -> dict[str, Any]:
    """For decisions whose visible result is derived: run the engines first, then read the result."""
    result = MentorService(session, clock).recalculate(trigger)
    meta = Meta(
        as_of_date=result.as_of_date,
        ruleset_version=result.ruleset_version,
        seed_version=result.seed_version,
        run_id=result.run_id,
    )
    return write_success(fetch(), meta, result.effects())
