from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.infrastructure.db import get_session
from app.repositories.system_repository import SystemRepository
from app.schemas.envelope import Meta, success
from app.services.health_service import HealthService

router = APIRouter(tags=["system"])


@router.get("/health")
def health(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    data = HealthService(SystemRepository(session), settings.ruleset_version).check()
    return success(data, Meta(ruleset_version=data.ruleset_version, seed_version=data.seed_version))
