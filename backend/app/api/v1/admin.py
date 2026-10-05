"""Admin: deterministic rebuild of every derived table from raw observations."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models import AuditLog
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.envelope import success
from app.services.catalog_service import CatalogService
from app.services.mentor_service import MentorService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/rebuild")
def rebuild(
    session: Annotated[Session, Depends(get_session)], clock: Annotated[Clock, Depends(get_clock)]
) -> dict[str, Any]:
    """Truncate evidence / skill states / snapshots and replay everything. Raw data is untouched."""
    CatalogService(CatalogRepository(session)).seed_version()  # 409 when no catalog is loaded
    result = MentorService(session, clock).rebuild()
    session.add(
        AuditLog(
            at=clock.now_utc().replace(tzinfo=None),
            entity_type="system",
            entity_id="derived",
            action="REBUILD_DERIVED",
            payload_json=result,
        )
    )
    session.commit()
    return success(result)
