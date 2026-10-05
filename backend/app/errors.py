"""Application error raised by services; translated to an error envelope by app/api/errors.py."""

from __future__ import annotations

from typing import Any

from app.schemas.envelope import ErrorCode


class AppError(Exception):
    def __init__(
        self, code: ErrorCode, message: str, status_code: int, details: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
