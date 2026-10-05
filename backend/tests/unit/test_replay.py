"""Deterministic replay: same ruleset + inputs + as_of_date + configuration -> identical result,
regardless of when (wall-clock) the computation runs."""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

import pytest

from app.domain.mentor_run import RunIdentity, build_run_identity
from app.domain.rulesets import fingerprint
from app.domain.rulesets.fingerprints import FROZEN_FINGERPRINTS

INPUTS: dict[str, object] = {
    "observations": [{"id": 1, "kind": "ATTEMPT", "outcome": "PASS", "observed_on": date(2026, 10, 1)}],
    "goal": {"target_date": date(2027, 6, 28), "weekday_budgets": (90, 90, 90, 90, 90, 75, 75)},
    "quality": Decimal("66.10"),
}


def run(as_of: date = date(2026, 10, 4), inputs: dict[str, object] | None = None) -> RunIdentity:
    return build_run_identity(
        as_of_date=as_of, ruleset_version="v1", seed_version="seed-v1", inputs=inputs or INPUTS
    )


def test_repeated_execution_is_identical() -> None:
    results = [run() for _ in range(50)]
    assert all(result == results[0] for result in results)


def test_wall_clock_time_does_not_affect_result(monkeypatch: pytest.MonkeyPatch) -> None:
    first = run()
    time.sleep(0.01)
    # Even if the process clock jumped years ahead, a replay for 2026-10-04 is unchanged.
    monkeypatch.setattr(time, "time", lambda: 4_102_444_800.0)  # 2100-01-01
    assert run() == first


def test_input_order_does_not_matter() -> None:
    reordered = {"quality": Decimal("66.1"), "goal": INPUTS["goal"], "observations": INPUTS["observations"]}
    assert run(inputs=reordered) == run()


def test_any_input_change_changes_the_hash() -> None:
    base = run().input_hash
    assert run(as_of=date(2026, 10, 5)).input_hash != base
    assert run(inputs={**INPUTS, "quality": Decimal("66.11")}).input_hash != base


def test_identity_records_ruleset_and_known_hash() -> None:
    identity = run()
    assert identity.ruleset_fingerprint == fingerprint("v1") == FROZEN_FINGERPRINTS["v1"]
    assert len(identity.input_hash) == 64


def test_unknown_ruleset_rejected() -> None:
    with pytest.raises(KeyError):
        build_run_identity(as_of_date=date(2026, 10, 4), ruleset_version="v0", seed_version="s", inputs={})


def test_float_inputs_rejected() -> None:
    with pytest.raises(TypeError):
        run(inputs={"score": 51.0})
