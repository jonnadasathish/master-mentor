"""Health check: application initialization + database connectivity (API_SPEC.md §2 /health)."""

from __future__ import annotations

import logging

from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.errors import AppError
from app.repositories.system_repository import SystemRepository
from app.schemas.envelope import ErrorCode

logger = logging.getLogger(__name__)


class HealthData(BaseModel):
    db: str  # "ok"
    ruleset_version: str
    seed_version: str | None  # null until the catalog seed is loaded (`make seed`)


class HealthService:
    def __init__(self, repository: SystemRepository, ruleset_version: str) -> None:
        self._repository = repository
        self._ruleset_version = ruleset_version

    def check(self) -> HealthData:
        try:
            self._repository.ping()
            seed_version = self._repository.loaded_seed_version()
        except SQLAlchemyError as exc:
            logger.warning("Database health check failed: %s", type(exc).__name__)
            raise AppError(
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                "Database is unreachable.",
                status_code=503,
                details={"db": "unreachable"},
            ) from exc
        return HealthData(db="ok", ruleset_version=self._ruleset_version, seed_version=seed_version)
