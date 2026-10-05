"""EVIDENCE_MODEL §7-§12 examples and the skill-state expectations of SCENARIOS.md."""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from app.domain.rulesets import v1
from app.domain.skills.state import calculate_skill_state
from tests.scenario_support import AS_OF, row


def state(rows: list, as_of=AS_OF):  # type: ignore[no-untyped-def]
    return calculate_skill_state("s.x", rows, as_of, v1)


def summary(rows: list) -> tuple:  # type: ignore[type-arg]
    return summary_at(rows, AS_OF)


def summary_at(rows: list, as_of) -> tuple:  # type: ignore[no-untyped-def, type-arg]
    s = state(rows, as_of)
    return (s.level, s.score, s.confidence, s.effective_score)


# ------------------------------------------------------------------ EVIDENCE_MODEL §12


def test_e1_two_clean_unseen_solves() -> None:
    assert summary([row(3, 100, 3, "p1"), row(3, 100, 10, "p2")]) == (3, 60, "LOW", 45)
    assert state([row(3, 100, 3, "p1"), row(3, 100, 10, "p2")]).label == "DEVELOPING"


def test_e2_graph_with_pattern_failures() -> None:
    rows = [
        row(3, 100, 4, "p1"),
        row(3, 100, 10, "p2"),
        row(3, 0, 1, "p3"),
        row(3, 0, 3, "p4"),
        row(3, 0, 6, "p5"),
    ]
    s = state(rows)
    assert (s.level, s.quality, s.score, s.confidence, s.effective_score) == (
        3,
        Decimal(40),
        51,
        "MEDIUM",
        44,
    )
    assert s.label == "WEAK"


def test_e3_timed_but_weak_explanation() -> None:
    assert summary([row(4, 100, 2, "a"), row(4, 100, 5, "b"), row(4, 100, 8, "c")]) == (4, 72, "MEDIUM", 65)


def test_e4_self_rating_has_no_effect() -> None:
    plain = [row(3, 100, 3, "p1"), row(3, 100, 10, "p2")]
    rated = [row(3, 100, 3, "p1", self_rating_before=5), row(3, 100, 10, "p2", self_rating_before=5)]
    assert summary(plain) == summary(rated)


def test_e5_decay_and_peak() -> None:
    s = state([row(4, 100, 130, "a"), row(4, 100, 135, "b"), row(3, 100, 140, "c")])
    assert (s.level, s.score, s.confidence, s.effective_score, s.peak_score) == (1, 30, "LOW", 15, 72)


# ------------------------------------------------------------------ SCENARIOS.md skill states


def test_s03_pattern_recognition_meta_skill() -> None:
    prior = [row(5, 100, age, f"q{age}") for age in (10, 15, 20, 25, 30, 35)]
    new = [
        row(3, 100, 4, "p1"),
        row(3, 100, 10, "p2"),
        row(3, 0, 1, "p3"),
        row(3, 0, 3, "p4"),
        row(3, 0, 6, "p5"),
    ]
    s = state(prior + new)
    assert (s.level, s.score, s.confidence, s.effective_score) == (5, 79, "HIGH", 79)
    assert round(s.quality, 2) == Decimal("66.10")  # type: ignore[arg-type]


def test_s05_leech_skill() -> None:
    rows = [
        row(3, 80, 41, "pa"),
        row(3, 75, 36, "pb"),
        row(3, 45, 16, "pc"),
        row(3, 30, 9, "pc"),
        row(3, 40, 1, "pc"),
    ]
    s = state(rows)
    assert (s.level, s.quality, s.score, s.confidence, s.effective_score, s.peak_score) == (
        3,
        Decimal("52.5"),
        53,
        "MEDIUM",
        46,
        53,
    )


def test_s06_overconfident_sliding_window() -> None:
    rows = [
        row(3, 100, 20, "a"),
        row(3, 100, 25, "b"),
        row(3, 0, 2, "c"),
        row(3, 0, 5, "d"),
        row(3, 0, 9, "e"),
        row(3, 50, 12, "f"),
    ]
    assert summary(rows) == (3, 51, "MEDIUM", 44)


def test_s07_s08_s09_states() -> None:
    timed = [row(4, 100, 3, "a"), row(4, 100, 6, "b"), row(4, 100, 10, "c")]
    assert summary(timed) == (4, 72, "MEDIUM", 65)  # S07 heap, S09 trees
    assert summary([row(3, 100, 3, "a"), row(3, 100, 7, "b"), row(3, 100, 11, "c")]) == (
        3,
        60,
        "MEDIUM",
        53,
    )  # S08
    think = state([row(4, 40, 2, "a"), row(4, 50, 5, "b"), row(4, 50, 8, "c")])  # S09 execution.think_aloud
    assert (think.level, think.score, think.confidence, think.effective_score) == (0, 5, "MEDIUM", 0)


def test_s17_interview_reality_cap() -> None:
    prior = [
        row(5, 100, 10, "a"),
        row(5, 100, 20, "b"),
        row(4, 100, 30, "c"),
        row(4, 100, 40, "d"),
        row(3, 100, 50, "e"),
        row(4, 60, 25, "f"),
    ]
    assert summary(prior) == (5, 81, "HIGH", 81)
    after = state(prior + [row(7, 40, 1, "m1")])
    assert (after.level, after.score, after.confidence, after.effective_score) == (5, 40, "HIGH", 40)
    assert after.reality_capped
    caching = [row(5, 100, a, f"c{a}") for a in (8, 16, 24)] + [
        row(4, 100, 32, "d"),
        row(4, 100, 40, "e"),
        row(3, 100, 50, "f"),
    ]
    assert state(caching).score == 82
    assert summary(caching + [row(7, 55, 1, "m1")]) == (5, 55, "HIGH", 55)


def test_reality_cap_expires_after_60_days_and_lifts_on_a_passing_mock() -> None:
    base = [row(5, 100, 70, "a"), row(5, 100, 75, "b")]
    assert state(base + [row(7, 40, 61, "m1")]).reality_capped is False
    assert state(base + [row(7, 40, 30, "m1"), row(7, 75, 5, "m2")]).reality_capped is False


def test_l7_needs_two_distinct_mock_rounds_of_75() -> None:
    base = [row(5, 100, 5, "a"), row(5, 100, 6, "b")]
    assert state(base + [row(7, 90, 2, "m1")]).level == 5
    assert state(base + [row(7, 90, 2, "m1"), row(7, 80, 3, "m2")]).level == 7
    # two mock rows >= 70 qualify L6 (rows at level >= 6); L7 needs both >= 75
    assert state(base + [row(7, 90, 2, "m1"), row(7, 74, 3, "m2")]).level == 6


# ------------------------------------------------------------------ general rules


def test_unassessed_and_declared_unknown() -> None:
    assert summary([]) == (None, None, "NONE", None)
    declared = row(0, 0, 3, "sa", is_scoring=False, kind="SELF_ASSESSMENT", familiarity="NONE")
    s = state([declared])
    assert (s.level, s.score, s.confidence, s.effective_score, s.declared_unknown) == (0, 0, "LOW", 0, True)
    later_some = row(0, 0, 1, "sa2", is_scoring=False, kind="SELF_ASSESSMENT", familiarity="SOME")
    assert state([declared, later_some]).confidence == "NONE"  # latest self-assessment wins


def test_self_assessment_never_raises_a_score() -> None:
    solid = row(0, 0, 1, "sa", is_scoring=False, kind="SELF_ASSESSMENT", familiarity="SOLID")
    assert summary([solid]) == (None, None, "NONE", None)


def test_rows_after_as_of_are_ignored() -> None:
    rows = [row(3, 100, 3, "p1"), row(3, 100, 10, "p2")]
    assert summary(rows) == (3, 60, "LOW", 45)
    # only the 10-day-old row is visible: one L3 row qualifies L1 only
    assert summary_at(rows, AS_OF - timedelta(days=5)) == (1, 30, "LOW", 15)


def test_input_order_does_not_change_state() -> None:
    rows = [
        row(3, 100, 4, "p1"),
        row(3, 0, 1, "p3"),
        row(4, 100, 3, "x"),
        row(4, 100, 7, "y"),
        row(3, 0, 6, "p5"),
    ]
    expected = state(rows)
    for seed in range(5):
        shuffled = rows[:]
        random.Random(seed).shuffle(shuffled)
        assert state(shuffled) == expected


def test_traceability_lists_considered_and_qualifying_rows() -> None:
    rows = [row(3, 100, 3, "p1"), row(3, 100, 10, "p2"), row(1, 90, 20, "q")]
    s = state(rows)
    assert {r.source_key for r in s.qualifying} == {"p1", "p2"}
    assert {r.source_key for r in s.considered} == {"p1", "p2"}  # L1 row below floor (level-1 = 2)
