"""Ruleset registry.

A ruleset is a frozen module of formula constants. Engines receive a ruleset explicitly; nothing reads
constants from configuration at call time. ``fingerprint(version)`` hashes every public UPPER_CASE
constant so that any value change is detectable (see ``fingerprints.FROZEN_FINGERPRINTS``).
"""

from __future__ import annotations

from types import ModuleType

from app.domain.canonical import sha256_hex
from app.domain.rulesets import v1

RULESETS: dict[str, ModuleType] = {v1.RULESET_VERSION: v1}


def get_ruleset(version: str) -> ModuleType:
    try:
        return RULESETS[version]
    except KeyError:
        raise KeyError(f"unknown ruleset version {version!r}; known: {sorted(RULESETS)}") from None


def constants(version: str) -> dict[str, object]:
    """All public constants of a ruleset except its version label."""
    module = get_ruleset(version)
    return {
        name: getattr(module, name)
        for name in sorted(dir(module))
        if name.isupper() and not name.startswith("_") and name != "RULESET_VERSION"
    }


def fingerprint(version: str) -> str:
    """SHA-256 of the canonical JSON of all constants of the ruleset."""
    return sha256_hex(constants(version))
