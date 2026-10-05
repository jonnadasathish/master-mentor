"""Sanity invariants of ruleset v1 against Specification v2 (catches transcription errors)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.rulesets import constants
from app.domain.rulesets import v1 as r


def test_all_constants_are_integer_or_text_only() -> None:
    """No floats or Decimals in rule constants (CLAUDE.md rule 10)."""

    def walk(value: object) -> None:
        assert not isinstance(value, float | Decimal), value
        if isinstance(value, dict) or hasattr(value, "items"):
            for k, v in value.items():  # type: ignore[attr-defined]
                walk(k)
                walk(v)
        elif isinstance(value, list | tuple):
            for v in value:
                walk(v)

    for value in constants("v1").values():
        walk(value)


def test_level_bands_are_contiguous_and_cover_0_to_100() -> None:
    bands = [r.LEVEL_BANDS[level] for level in range(8)]
    assert bands[0][0] == 0 and bands[-1][1] == 100
    for (_, hi), (lo, _) in zip(bands, bands[1:], strict=False):
        assert hi == lo


def test_qualification_is_monotonic_and_l7_requires_two_mocks() -> None:
    assert r.QUALIFICATION[7] == (2, 2, 75)  # D-030
    mins = [r.QUALIFICATION[level][2] for level in range(1, 8)]
    assert mins == sorted(mins)


def test_recency_steps_are_ascending_and_decaying() -> None:
    ages = [age for age, _ in r.RECENCY_BP]
    weights = [bp for _, bp in r.RECENCY_BP] + [r.RECENCY_BP_OLDER]
    assert ages == sorted(ages) and ages[-1] == r.LEVEL_WINDOW_DAYS
    assert weights == sorted(weights, reverse=True)


def test_revision_ladders_strictly_increase() -> None:
    for ladder in (r.STANDARD_INTERVALS, r.MOCKW_INTERVALS):
        assert list(ladder) == sorted(set(ladder))
    assert r.STANDARD_INTERVALS == (1, 3, 7, 14, 30, 60)


def test_pressure_terms_fit_under_cap() -> None:
    maximum = (
        r.PRESSURE_BASE_BP
        + r.FAILURE_BP_PER_FAIL * r.FAILURE_MAX_COUNTED
        + r.MOCK_BP
        + r.GATE_BP
        + r.FLOOR_BP
        + r.RETENTION_BP
    )
    assert r.PRESSURE_BASE_BP < r.PRESSURE_CAP_BP < maximum  # cap is binding but above base


def test_status_thresholds_descend() -> None:
    values = [threshold for _, threshold in r.STATUS_THRESHOLDS]
    assert values == sorted(values, reverse=True) == [60, 40, 25, 10]


def test_min_per_point_covers_all_seven_components() -> None:
    assert set(r.MIN_PER_POINT) == {"dsa", "coding", "cs", "lld", "system_design", "behavioral", "project"}


def test_revision_cap_fits_a_reinforced_medium_problem_at_default_budget() -> None:
    cap = max(r.REVISION_CAP_MIN_MINUTES, 90 * r.REVISION_CAP_PCT // 100)
    assert cap >= r.REVISION_ITEM_MINUTES["PROBLEM_MEDIUM"] + r.REINFORCE_EXTRA_MINUTES  # D-016


def test_message_rules_are_unique_and_end_with_default() -> None:
    assert len(r.MESSAGE_RULE_ORDER) == len(set(r.MESSAGE_RULE_ORDER)) == 21
    assert r.MESSAGE_RULE_ORDER[0] == "CALIBRATION" and r.MESSAGE_RULE_ORDER[-1] == "DEFAULT"


def test_gap_types_start_with_unassessed_and_end_with_level_up() -> None:
    assert r.GAP_TYPE_ORDER[0] == "UNASSESSED" and r.GAP_TYPE_ORDER[-1] == "LEVEL_UP"
    assert len(r.GAP_TYPE_ORDER) == 13


def test_level_up_stage_covers_every_level() -> None:
    assert set(r.LEVEL_UP_STAGE) == set(range(8))
    assert set(r.LEVEL_UP_STAGE.values()) <= set(r.STAGE_LADDER)
