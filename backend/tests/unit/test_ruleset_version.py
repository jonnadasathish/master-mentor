"""Version-bump protection (CLAUDE.md rule 12).

If any formula/rule constant changes, the ruleset version must change. Mechanism: every released
ruleset has a frozen fingerprint; recomputing it must give the same value.
"""

from __future__ import annotations

import pytest

from app.domain.rulesets import RULESETS, constants, fingerprint
from app.domain.rulesets.fingerprints import FROZEN_FINGERPRINTS


@pytest.mark.parametrize("version", sorted(RULESETS))
def test_released_ruleset_constants_are_unchanged(version: str) -> None:
    assert version in FROZEN_FINGERPRINTS, (
        f"ruleset {version!r} has no frozen fingerprint; add fingerprint({version!r}) to fingerprints.py"
    )
    actual = fingerprint(version)
    assert actual == FROZEN_FINGERPRINTS[version], (
        f"Constants of ruleset {version!r} changed (fingerprint {actual} != frozen "
        f"{FROZEN_FINGERPRINTS[version]}). Released rulesets are immutable: revert the change, or create the "
        "next ruleset version, register it, freeze its fingerprint, and add a DECISION_LOG entry."
    )


def test_every_frozen_fingerprint_belongs_to_a_registered_ruleset() -> None:
    assert set(FROZEN_FINGERPRINTS) == set(RULESETS)


@pytest.mark.parametrize("version", sorted(RULESETS))
def test_module_version_label_matches_registry_key(version: str) -> None:
    assert version == RULESETS[version].RULESET_VERSION


def test_versions_have_distinct_fingerprints() -> None:
    values = list(FROZEN_FINGERPRINTS.values())
    assert len(values) == len(set(values)), "a new ruleset version must change at least one constant"


def test_fingerprint_detects_any_constant_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mechanism itself: changing one value changes the fingerprint."""
    module = RULESETS["v1"]
    before = fingerprint("v1")
    monkeypatch.setattr(module, "LEECH_LAPSES", module.LEECH_LAPSES + 1)
    assert fingerprint("v1") != before


def test_fingerprint_detects_new_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    module = RULESETS["v1"]
    before = fingerprint("v1")
    monkeypatch.setattr(module, "SNEAKY_NEW_CONSTANT", 1, raising=False)
    assert fingerprint("v1") != before


def test_version_label_is_not_part_of_fingerprint() -> None:
    assert "RULESET_VERSION" not in constants("v1")
