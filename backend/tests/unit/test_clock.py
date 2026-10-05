"""Clock rule: domain code never reads the real clock; services get dates from a Clock."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.domain.clock import FixedClock, local_date, today_local
from app.infrastructure.clock import SystemClock

APP_DIR = Path(__file__).resolve().parents[2] / "app"
FORBIDDEN_CALLS = {
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("datetime", "today"),
    ("date", "today"),
    ("time", "time"),
    ("time", "time_ns"),
    ("time", "localtime"),
    ("time", "gmtime"),
}


def _clock_reads(path: Path) -> list[str]:
    hits = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            name = owner.attr if isinstance(owner, ast.Attribute) else getattr(owner, "id", None)
            if (name, node.func.attr) in FORBIDDEN_CALLS:
                shown = path.relative_to(APP_DIR.parent) if path.is_relative_to(APP_DIR.parent) else path.name
                hits.append(f"{shown}:{node.lineno} {name}.{node.func.attr}()")
    return hits


def test_domain_code_never_reads_the_real_clock() -> None:
    hits = [hit for path in sorted((APP_DIR / "domain").rglob("*.py")) for hit in _clock_reads(path)]
    assert hits == [], "domain must take as_of_date / a Clock instead of reading time: " + ", ".join(hits)


def test_system_clock_is_the_only_real_clock_reader_in_the_app() -> None:
    readers = sorted({hit.split(":")[0] for path in APP_DIR.rglob("*.py") for hit in _clock_reads(path)})
    assert readers == ["app/infrastructure/clock.py"]


def test_scanner_detects_violations(tmp_path: Path) -> None:
    sample = tmp_path / "x.py"
    sample.write_text(
        "import datetime\nfrom datetime import date\na = datetime.datetime.now()\nb = date.today()\n"
    )
    assert len(_clock_reads(sample)) == 2


def test_fixed_clock_is_frozen_and_utc() -> None:
    instant = datetime(2026, 10, 4, 9, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    clock = FixedClock(instant)
    assert clock.now_utc() == clock.now_utc() == datetime(2026, 10, 4, 4, 0, tzinfo=UTC)
    assert clock.now_utc().tzinfo == UTC


def test_fixed_clock_rejects_naive_instants() -> None:
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 10, 4, 9, 0))


def test_local_date_uses_user_timezone_across_midnight() -> None:
    # 20:00 UTC on 4 Oct is 01:30 on 5 Oct in India: the user's "today" is the 5th.
    instant = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)
    assert local_date(instant, "Asia/Kolkata").isoformat() == "2026-10-05"
    assert local_date(instant, "UTC").isoformat() == "2026-10-04"
    assert today_local(FixedClock(instant), "Asia/Kolkata").isoformat() == "2026-10-05"


def test_local_date_rejects_naive_instants() -> None:
    with pytest.raises(ValueError):
        local_date(datetime(2026, 10, 4), "UTC")


def test_system_clock_returns_aware_utc_now() -> None:
    now = SystemClock().now_utc()
    assert now.tzinfo == UTC
