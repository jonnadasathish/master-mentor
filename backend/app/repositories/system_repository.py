"""System-level data access (connectivity)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

MYSQL_NO_SUCH_TABLE = 1146


class SystemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ping(self) -> None:
        """Raise if the database is unreachable."""
        self._session.execute(text("SELECT 1")).scalar_one()

    def loaded_seed_version(self) -> str | None:
        """seed_version of the latest catalog load; None if never loaded or not yet migrated."""
        try:
            value = self._session.execute(
                text("SELECT seed_version FROM catalog_loads ORDER BY id DESC LIMIT 1")
            ).scalar_one_or_none()
        except ProgrammingError as exc:
            if getattr(exc.orig, "args", [None])[0] == MYSQL_NO_SUCH_TABLE:
                self._session.rollback()
                return None
            raise
        return str(value) if value is not None else None
