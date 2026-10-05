"""Backup status through the API, and the backend's view of the shared ./backups bind mount (D-075, D-077).

The `backup` service writes ./backups; the backend reads the same host directory read-only at /backups. A
backend container created before that mount existed reported "No backup found" although backups were
verified (D-077). The cross-container check (backup container ↔ backend ↔ endpoint) is
`make backup-status-check`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_clock
from app.config import get_settings
from app.domain.clock import FixedClock
from app.main import create_app
from app.services.backup_status import parse_latest

NOW = datetime(2026, 10, 5, 6, 0, tzinfo=UTC)
IN_CONTAINER = Path("/.dockerenv").exists()
needs_compose_backend = pytest.mark.skipif(
    not IN_CONTAINER, reason="the /backups mount exists only in the compose backend container"
)


@pytest.fixture
def backup_dir_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    """Lets a test point BACKUP_DIR elsewhere; the cached settings are rebuilt before and after."""
    get_settings.cache_clear()
    yield monkeypatch
    monkeypatch.undo()
    get_settings.cache_clear()


def fetch_status(clock: FixedClock | None = None) -> dict[str, Any]:
    app = create_app()
    if clock is not None:
        app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/system/backup-status")
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_endpoint_reports_the_file_named_in_latest(
    backup_dir_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "mastermentor-20261005T055446Z.sql.gz").write_bytes(b"")
    (tmp_path / "LATEST").write_text("20261005T055446Z mastermentor-20261005T055446Z.sql.gz\n")
    backup_dir_env.setenv("BACKUP_DIR", str(tmp_path))
    status = fetch_status(FixedClock(NOW))
    assert status == {
        "available": True,
        "latest_file": "mastermentor-20261005T055446Z.sql.gz",
        "taken_at": "2026-10-05T05:54:46Z",
        "age_hours": 0,
        "warning": False,
        "max_age_hours": 36,
        "message": "Last backup is 0 h old.",
    }


def test_endpoint_warns_when_the_directory_is_not_mounted(
    backup_dir_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    backup_dir_env.setenv("BACKUP_DIR", str(tmp_path / "not-mounted"))
    status = fetch_status(FixedClock(NOW))
    assert (status["available"], status["warning"], status["message"]) == (
        False,
        True,
        "No backup found. Run `make backup`.",
    )


@needs_compose_backend
def test_backend_container_mounts_the_shared_backup_directory_read_only() -> None:
    backup_dir = Path(get_settings().backup_dir)
    assert backup_dir == Path("/backups")
    assert backup_dir.is_dir(), "backend has no /backups: recreate it with `docker compose up -d` (D-077)"
    assert not os.access(backup_dir, os.W_OK), "/backups must be mounted read-only in the backend"


@needs_compose_backend
def test_endpoint_reports_what_the_shared_directory_holds() -> None:
    backup_dir = Path(get_settings().backup_dir)
    latest = backup_dir / "LATEST"
    status = fetch_status()
    if not latest.exists():  # fresh checkout: no backup taken yet
        assert (status["available"], status["warning"]) == (False, True)
        return
    parsed = parse_latest(latest.read_text(encoding="utf-8"))
    assert parsed is not None, f"unreadable LATEST: {latest.read_text(encoding='utf-8')!r}"
    taken, name = parsed
    assert (backup_dir / name).is_file(), f"LATEST names {name}, which is not in {backup_dir}"
    assert status["available"] is True
    assert (status["latest_file"], status["taken_at"]) == (name, taken.isoformat().replace("+00:00", "Z"))
