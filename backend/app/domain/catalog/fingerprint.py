"""Seed fingerprints: identify the exact seed inputs that populated the database.

A file fingerprint is the SHA-256 of the canonical JSON of the parsed YAML (so comments and formatting do not
matter, content does). The catalog fingerprint combines all file fingerprints. ``seed.lock.yaml`` freezes the
fingerprints of every released ``seed_version``; changing seed content without bumping the version fails
validation (same principle as the ruleset fingerprints, but an independent version line).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.domain.canonical import sha256_hex
from app.domain.catalog.issues import Issue


def file_fingerprints(raw: Mapping[str, object]) -> dict[str, str]:
    """``raw`` maps a file role (e.g. "skill_graph", "role_profile:<key>") to its parsed YAML."""
    return {role: sha256_hex(raw[role]) for role in sorted(raw)}


def catalog_fingerprint(files: Mapping[str, str]) -> str:
    return sha256_hex(dict(files))


def check_lock(
    seed_version: str, files: Mapping[str, str], lock: Mapping[str, object], *, lock_name: str
) -> list[Issue]:
    entry = lock.get(seed_version)
    if entry is None:
        return [
            Issue(
                "lock.unlocked_version",
                lock_name,
                f"seed_version {seed_version!r} has no frozen fingerprints. If this is a new version, "
                "run `make seed-lock`; otherwise restore the files of a locked version.",
            )
        ]
    if not isinstance(entry, Mapping) or not isinstance(entry.get("files"), Mapping):
        return [Issue("lock.malformed", f"{lock_name}: {seed_version}", "expected a mapping with 'files'")]
    frozen: Mapping[str, object] = entry["files"]
    issues: list[Issue] = []
    for role in sorted(set(frozen) | set(files)):
        if frozen.get(role) != files.get(role):
            issues.append(
                Issue(
                    "lock.changed_without_version_bump",
                    f"{lock_name}: {seed_version}.files.{role}",
                    f"content of {role!r} differs from the frozen {seed_version} fingerprint. Released seed "
                    "versions are immutable: revert the change, or bump seed_version in every seed file, "
                    "run `make seed-lock`, and add a DECISION_LOG entry.",
                )
            )
    return issues
