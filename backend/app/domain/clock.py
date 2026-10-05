"""Clock abstraction (Spec v2 determinism rule).

Domain engines never read the real clock. They take ``as_of_date`` (a local calendar date) as an
argument. Services obtain that date from a ``Clock``: ``SystemClock`` in production
(app/infrastructure/clock.py, the only module allowed to read the system time) or ``FixedClock`` in tests and
replays.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def now_utc(self) -> datetime:
        """Current instant, timezone-aware, in UTC."""
        ...


def local_date(instant: datetime, timezone: str) -> date:
    """The calendar date of ``instant`` in the IANA ``timezone`` (pure conversion)."""
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    return instant.astimezone(ZoneInfo(timezone)).date()


def today_local(clock: Clock, timezone: str) -> date:
    """``as_of_date`` for a service call: today's date in the user's timezone according to ``clock``."""
    return local_date(clock.now_utc(), timezone)


@dataclass(frozen=True)
class FixedClock:
    """A clock frozen at one instant. Used by tests and deterministic replays."""

    instant: datetime

    def __post_init__(self) -> None:
        if self.instant.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware instant")

    def now_utc(self) -> datetime:
        return self.instant.astimezone(UTC)
