"""Backup age (D-075): reads LATEST written by scripts/backup-once.sh from the read-only ./backups mount."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_latest(line: str) -> tuple[datetime, str] | None:
    """``"20261005T044331Z mastermentor-20261005T044331Z.sql.gz"`` -> (UTC instant, file name)."""
    parts = line.strip().split()
    if len(parts) != 2:
        return None
    try:
        taken = datetime.strptime(parts[0], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return taken, parts[1]


def backup_status(backup_dir: str, now: datetime, max_age_hours: int) -> dict[str, Any]:
    latest = Path(backup_dir) / "LATEST"
    try:
        parsed = parse_latest(latest.read_text(encoding="utf-8"))
    except OSError:
        parsed = None
    if parsed is None:
        return {
            "available": False,
            "latest_file": None,
            "taken_at": None,
            "age_hours": None,
            "warning": True,
            "max_age_hours": max_age_hours,
            "message": "No backup found. Run `make backup`.",
        }
    taken, name = parsed
    age_hours = int((now - taken).total_seconds() // 3600)
    warning = age_hours >= max_age_hours
    return {
        "available": True,
        "latest_file": name,
        "taken_at": taken.isoformat().replace("+00:00", "Z"),
        "age_hours": age_hours,
        "warning": warning,
        "max_age_hours": max_age_hours,
        "message": f"Last backup is {age_hours} h old."
        + (" Run `make backup` and check the backup service." if warning else ""),
    }
