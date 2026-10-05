"""Shared FastAPI dependencies (overridable in tests)."""

from __future__ import annotations

from app.domain.clock import Clock
from app.infrastructure.clock import SystemClock


def get_clock() -> Clock:
    return SystemClock()
