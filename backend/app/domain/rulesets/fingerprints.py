"""Frozen fingerprints of every released ruleset.

A fingerprint is the SHA-256 of the canonical JSON of all constants of the ruleset module
(``app.domain.rulesets.fingerprint``). Entries are append-only: never edit an existing value.

If ``tests/unit/test_ruleset_version.py`` fails because a fingerprint changed, you changed a frozen
ruleset. Revert the change, or create the next version (copy v1.py to v2.py, set RULESET_VERSION,
register it, add its fingerprint here, add a DECISION_LOG entry, recompute SCENARIOS.md).
"""

from __future__ import annotations

from typing import Final

FROZEN_FINGERPRINTS: Final[dict[str, str]] = {
    "v1": "00d06a3cd203b4d308eb704855ca2e0fc8280258a5d0c7cf133f3b5a85fdfe16",
}
