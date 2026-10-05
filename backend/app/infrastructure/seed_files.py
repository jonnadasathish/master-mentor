"""Reading the canonical seed files and appending to the seed lock (file I/O lives here, not in domain)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from app.domain.catalog import vocabulary as v


class SeedFileError(Exception):
    """A seed file exists but cannot be parsed as YAML."""


def _load_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise SeedFileError(f"{path.name}: invalid YAML: {exc}") from exc


def read_seed(seed_dir: str | Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return (raw seed by file role, lock data).

    Missing files are simply absent from the result; the validator reports them."""
    root = Path(seed_dir)
    raw: dict[str, Any] = {}
    for role, name in v.SEED_FILES.items():
        path = root / name
        if path.is_file():
            raw[role] = _load_yaml(path)
    profile_dir = root / v.ROLE_PROFILE_DIR
    if profile_dir.is_dir():
        for path in sorted(profile_dir.glob("*.yaml")):
            raw[f"role_profile:{path.stem}"] = _load_yaml(path)
    lock_path = root / v.LOCK_FILE
    lock = _load_yaml(lock_path) if lock_path.is_file() else None
    if lock is not None and not isinstance(lock, dict):
        raise SeedFileError(f"{v.LOCK_FILE}: expected a mapping of seed_version -> fingerprints")
    return raw, lock


LOCK_HEADER = """\
# Frozen fingerprints of every released seed_version (append-only; written by `make seed-lock`).
# A fingerprint is the SHA-256 of the canonical JSON of the parsed YAML file, so comments and formatting
# do not matter but any content change does. Changing a locked version's content fails validation:
# bump seed_version in every seed file, run `make seed-lock`, and add a DECISION_LOG entry.
"""


def append_lock_entry(
    seed_dir: str | Path, seed_version: str, files: Mapping[str, str], catalog_fingerprint: str
) -> Path:
    path = Path(seed_dir) / v.LOCK_FILE
    _, existing = read_seed(seed_dir)
    existing = existing or {}
    if seed_version in existing:
        raise SeedFileError(f"{seed_version} is already locked; released seed versions are immutable")
    entry = {seed_version: {"catalog": catalog_fingerprint, "files": dict(sorted(files.items()))}}
    body = yaml.safe_dump(entry, sort_keys=False)
    if not path.exists():
        path.write_text(LOCK_HEADER + body, encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(body)
    return path
