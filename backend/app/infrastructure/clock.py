"""System clock: the ONLY place in the application that reads the real time."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now_utc(self) -> datetime:
        return datetime.now(UTC)
