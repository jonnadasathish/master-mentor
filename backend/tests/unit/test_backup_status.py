"""Backup age warning (D-075): parse LATEST, warn when missing or older than the threshold."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.services.backup_status import backup_status, parse_latest

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def test_parse_latest() -> None:
    assert parse_latest("20261003T120000Z mastermentor-x.sql.gz\n") == (
        datetime(2026, 10, 3, 12, tzinfo=UTC),
        "mastermentor-x.sql.gz",
    )
    assert parse_latest("garbage") is None
    assert parse_latest("2026-10-03 file.sql.gz") is None


def test_fresh_backup_has_no_warning_and_old_or_missing_warns(tmp_path: Path) -> None:
    (tmp_path / "LATEST").write_text("20261003T120000Z mastermentor-20261003T120000Z.sql.gz\n")
    fresh = backup_status(str(tmp_path), NOW, 36)
    assert (fresh["available"], fresh["age_hours"], fresh["warning"]) == (True, 24, False)
    old = backup_status(str(tmp_path), datetime(2026, 10, 5, 2, tzinfo=UTC), 36)
    assert (old["age_hours"], old["warning"]) == (38, True) and "make backup" in old["message"]
    missing = backup_status(str(tmp_path / "nope"), NOW, 36)
    assert (missing["available"], missing["warning"]) == (False, True)
