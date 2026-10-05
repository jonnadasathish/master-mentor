from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.activity.rules import attempt_errors

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def errors(**overrides: object) -> list[str]:
    values: dict[str, object] = dict(
        attempted_at=NOW, now_utc=NOW, timed=False, time_seconds=600, time_limit_seconds=None, mistakes=()
    )
    values.update(overrides)
    return [e.field for e in attempt_errors(**values)]  # type: ignore[arg-type]


def test_plain_attempt_is_valid() -> None:
    assert errors() == []


def test_future_attempt_rejected_but_small_skew_allowed() -> None:
    assert errors(attempted_at=NOW + timedelta(minutes=10)) == ["attempted_at"]
    assert errors(attempted_at=NOW + timedelta(minutes=4)) == []


def test_naive_datetime_rejected() -> None:
    assert errors(attempted_at=datetime(2026, 10, 4, 11, 0)) == ["attempted_at"]


def test_timed_attempt_needs_limit_and_time() -> None:
    assert errors(timed=True, time_seconds=None) == ["time_limit_seconds", "time_seconds"]
    assert errors(timed=True, time_limit_seconds=1800) == []
    assert errors(timed=False, time_limit_seconds=1800) == ["time_limit_seconds"]


def test_duplicate_mistakes_rejected() -> None:
    assert errors(mistakes=("WRONG_PATTERN", "WRONG_PATTERN")) == ["mistakes"]
