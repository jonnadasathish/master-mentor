"""Mentor-run identity (the deterministic part of a ``mentor_runs`` row).

Spec v2: the same observations/decisions, ``as_of_date``, goal, ``ruleset_version`` and ``seed_version``
must produce identical outputs. Slice 1 provides the identity/hash of a run's inputs; the engines that
consume the inputs arrive in later slices and receive the same explicit arguments.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from app.domain.canonical import sha256_hex
from app.domain.rulesets import fingerprint, get_ruleset


@dataclass(frozen=True)
class RunIdentity:
    as_of_date: date
    ruleset_version: str
    ruleset_fingerprint: str
    seed_version: str
    input_hash: str  # 64 hex chars, stored in mentor_runs.input_hash


def build_run_identity(
    *,
    as_of_date: date,
    ruleset_version: str,
    seed_version: str,
    inputs: Mapping[str, object],
) -> RunIdentity:
    """Deterministically identify a mentor run from its explicit inputs (no clock, no I/O)."""
    get_ruleset(ruleset_version)  # unknown version -> KeyError
    ruleset_fp = fingerprint(ruleset_version)
    input_hash = sha256_hex(
        {
            "as_of_date": as_of_date,
            "ruleset_version": ruleset_version,
            "ruleset_fingerprint": ruleset_fp,
            "seed_version": seed_version,
            "inputs": inputs,
        }
    )
    return RunIdentity(
        as_of_date=as_of_date,
        ruleset_version=ruleset_version,
        ruleset_fingerprint=ruleset_fp,
        seed_version=seed_version,
        input_hash=input_hash,
    )
