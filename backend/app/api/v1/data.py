"""Import (preview / commit) and backup status. Import never overwrites: it only fills an empty database."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.config import get_settings
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.schemas.envelope import success
from app.services.backup_status import backup_status
from app.services.import_service import ImportService

router = APIRouter(tags=["data"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


class ImportCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: dict[str, Any]
    confirm: str = Field(max_length=64)


@router.post("/import/preview")
def import_preview(session: DbSession, clock: ClockDep, document: dict[str, Any]) -> dict[str, Any]:
    """Validates a JSON export (v2) against this database; writes nothing."""
    return success(ImportService(session, clock).preview(document))


@router.post("/import/commit")
def import_commit(session: DbSession, clock: ClockDep, payload: ImportCommit) -> dict[str, Any]:
    """Atomic import into an empty database (needs ``confirm``), then a deterministic rebuild."""
    return success(ImportService(session, clock).commit(payload.document, payload.confirm))


@router.get("/system/backup-status")
def get_backup_status(clock: ClockDep) -> dict[str, Any]:
    settings = get_settings()
    return success(backup_status(settings.backup_dir, clock.now_utc(), settings.backup_max_age_hours))
