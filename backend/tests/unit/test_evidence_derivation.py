"""EVIDENCE_MODEL §4-§5 derivation rules (observation -> evidence rows)."""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.evidence.derive import attempt_level, derive_evidence, outcome_points
from app.domain.evidence.model import (
    AssessmentObservation,
    AssessmentSkillInput,
    EvidenceRow,
    MockRoundObservation,
    MockRoundSkillInput,
    SkillInfo,
)
from app.domain.rulesets import v1
from tests.scenario_support import attempt

SKILLS = {
    k: SkillInfo(k, "dsa", True)
    for k in [
        "s.x",
        "s.y",
        "dsa.pattern_recognition",
        "dsa.complexity_analysis",
        "execution.followup_handling",
        "execution.clarification",
        "execution.think_aloud",
        "execution.testing_dry_run",
        "execution.time_management",
        "execution.brute_force_to_optimal",
        "execution.bug_free_coding",
        "python.core_syntax",
        "python.collections",
        "db.indexing",
        "behavioral.ownership",
    ]
}


def rows_for(*attempts, assessments=(), mocks=()) -> list[EvidenceRow]:  # type: ignore[no-untyped-def]
    return derive_evidence(
        attempts=list(attempts),
        assessments=list(assessments),
        mock_rounds=list(mocks),
        skills=SKILLS,
        ruleset=v1,
    )


def by_skill(rows: list[EvidenceRow]) -> dict[str, EvidenceRow]:
    return {r.skill: r for r in rows}


# ------------------------------------------------------------------ §4 outcome points


@pytest.mark.parametrize(
    ("kwargs", "points"),
    [
        ({"outcome": "FAIL"}, 0),
        ({"outcome": "PASS", "solution_viewed": True}, 20),
        ({"outcome": "PARTIAL"}, 50),
        ({"outcome": "PASS", "hints_used": 2}, 60),
        ({"outcome": "PASS", "hints_used": 1}, 80),
        ({"outcome": "PASS"}, 100),
    ],
)
def test_outcome_points(kwargs: dict[str, object], points: int) -> None:
    assert outcome_points(attempt(1, **kwargs), v1) == points


# ------------------------------------------------------------------ §5.1 levels


@pytest.mark.parametrize(
    ("kwargs", "level"),
    [
        ({}, 3),
        ({"hints_used": 1}, 2),
        ({"solution_viewed": True}, 2),
        ({"timed": True, "time_limit_seconds": 1800, "time_seconds": 1500}, 4),
        ({"timed": True, "time_limit_seconds": 1800, "time_seconds": 1900}, 3),  # over the limit
        ({"timed": True, "time_limit_seconds": 2400, "time_seconds": 1500}, 3),  # limit > expected (30 min)
        (
            {
                "timed": True,
                "time_limit_seconds": 1800,
                "time_seconds": 1500,
                "explanation_score": 7,
                "complexity_correct": True,
            },
            5,
        ),
        (
            {
                "timed": True,
                "time_limit_seconds": 1800,
                "time_seconds": 1500,
                "explanation_score": 6,
                "complexity_correct": True,
            },
            4,
        ),
        (
            {
                "timed": True,
                "time_limit_seconds": 1800,
                "time_seconds": 1500,
                "explanation_score": 8,
                "complexity_correct": True,
                "followup_solved": True,
            },
            6,
        ),
        (
            {
                "difficulty": "HARD",
                "timed": True,
                "time_limit_seconds": 2700,
                "time_seconds": 2000,
                "explanation_score": 8,
                "complexity_correct": True,
            },
            6,
        ),
        (
            {"difficulty": "EASY", "timed": True, "time_limit_seconds": 900, "time_seconds": 600},
            3,
        ),  # EASY cap
        ({"seen_elsewhere": True, "timed": True, "time_limit_seconds": 1800, "time_seconds": 1500}, 3),
    ],
)
def test_attempt_level_ladder(kwargs: dict[str, object], level: int) -> None:
    assert attempt_level(attempt(1, **kwargs), [], v1) == level


def test_repeat_of_a_seen_problem_is_memory_not_solving() -> None:
    first = attempt(1, day=date(2026, 10, 1))
    within_week = attempt(2, day=date(2026, 10, 5), timed=True, time_limit_seconds=1800, time_seconds=900)
    later = attempt(3, day=date(2026, 10, 20), timed=True, time_limit_seconds=1800, time_seconds=900)
    assert attempt_level(within_week, [first], v1) == 1
    assert attempt_level(later, [first], v1) == 3
    rows = rows_for(later, first, within_week)  # input order must not matter
    mapped = [r for r in rows if r.skill == "s.x"]
    assert [(r.source_id, r.level, r.is_unseen) for r in mapped] == [
        (1, 3, True),
        (2, 1, False),
        (3, 3, False),
    ]


# ------------------------------------------------------------------ §5.2 derived rows and §5.3 mistakes


def test_derived_rows_and_mistake_routing() -> None:
    a = attempt(
        1,
        outcome="FAIL",
        timed=True,
        time_limit_seconds=1800,
        time_seconds=1700,
        pattern_identified=False,
        complexity_correct=False,
        followup_solved=False,
        execution_rubric={"think_aloud": 4, "clarification": 8},
        mistakes=("WRONG_PATTERN", "LANGUAGE_SYNTAX", "WRONG_COMPLEXITY"),
    )
    rows = by_skill(rows_for(a))
    assert rows["s.x"].rule == "MAPPED" and rows["s.x"].outcome_points == 0 and rows["s.x"].level == 4
    assert (rows["dsa.pattern_recognition"].outcome_points, rows["dsa.pattern_recognition"].level) == (0, 4)
    assert rows["dsa.complexity_analysis"].outcome_points == 0
    assert rows["execution.followup_handling"].outcome_points == 0
    assert rows["execution.think_aloud"].outcome_points == 40
    assert rows["execution.think_aloud"].communication_points == 40
    assert rows["execution.clarification"].outcome_points == 80
    assert rows["python.core_syntax"].rule == "MISTAKE" and rows["python.core_syntax"].outcome_points == 0
    assert rows["execution.brute_force_to_optimal"].outcome_points == 0  # WRONG_COMPLEXITY route
    assert "execution.bug_free_coding" not in rows  # FAIL: no bug-free row
    assert rows["s.x"].time_ratio_bp == 1700 * 10000 // 1800


def test_merge_keeps_minimum_points_and_highest_precedence_level() -> None:
    a = attempt(1, mappings=(("dsa.complexity_analysis", 10000),), complexity_correct=False)
    rows = by_skill(rows_for(a))
    merged = rows["dsa.complexity_analysis"]
    assert (merged.rule, merged.outcome_points) == ("MAPPED", 0)  # PASS 100 merged with derived 0


def test_bug_free_coding_rules() -> None:
    clean = by_skill(rows_for(attempt(1)))["execution.bug_free_coding"]
    buggy = by_skill(rows_for(attempt(2, problem_id=2, mistakes=("OFF_BY_ONE",))))[
        "execution.bug_free_coding"
    ]
    partial = by_skill(rows_for(attempt(3, problem_id=3, outcome="PARTIAL")))["execution.bug_free_coding"]
    assert (clean.outcome_points, buggy.outcome_points, partial.outcome_points) == (
        100,
        0,
        0,
    )  # OFF_BY_ONE row min
    assert "execution.bug_free_coding" not in by_skill(rows_for(attempt(4, problem_id=4, hints_used=1)))
    assert "execution.bug_free_coding" not in by_skill(
        rows_for(attempt(5, problem_id=5, pattern_identified=False))
    )


def test_pattern_recognition_only_for_unseen_attempts() -> None:
    first = attempt(1, pattern_identified=True)
    repeat = attempt(2, day=date(2026, 10, 31), pattern_identified=True)
    rows = rows_for(first, repeat)
    assert [r.source_id for r in rows if r.skill == "dsa.pattern_recognition"] == [1]


# ------------------------------------------------------------------ §5.4 assessments, §5.5 mocks


def assessment(
    kind: str, points: int | None = 80, skill: str = "db.indexing", **kw: object
) -> AssessmentObservation:
    day = date(2026, 10, 30)
    values: dict[str, object] = dict(
        id=10,
        kind=kind,
        observed_on=day,
        observed_at=datetime(2026, 10, 30, 6, tzinfo=UTC),
        source_key="prompt:x",
        skills=(AssessmentSkillInput(skill, points),),
    )
    values.update(kw)
    return AssessmentObservation(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kind", "kwargs", "level", "scoring"),
    [
        ("STUDY_SESSION", {}, 0, False),
        ("SELF_ASSESSMENT", {"familiarity": "NONE"}, 0, False),
        ("RECALL_QUIZ", {}, 1, True),
        ("RECALL_QUIZ", {"notes_used": True}, 0, False),
        ("CONCEPT_EXPLAIN", {"notes_used": True}, 2, True),
        ("CONCEPT_EXPLAIN", {}, 3, True),
        ("CONCEPT_EXPLAIN", {"timed": True, "time_limit_seconds": 900, "time_seconds": 800}, 4, True),
        (
            "CONCEPT_EXPLAIN",
            {"timed": True, "time_limit_seconds": 900, "time_seconds": 800, "followup_points": 70},
            5,
            True,
        ),
        (
            "SD_DESIGN",
            {
                "timed": True,
                "time_limit_seconds": 2700,
                "time_seconds": 2600,
                "followup_points": 75,
                "peer_evaluated": True,
            },
            6,
            True,
        ),
        ("APPLIED_TASK", {"followup_points": 70}, 6, True),
        ("APPLIED_TASK", {"followup_points": 60}, 3, True),
    ],
)
def test_assessment_levels(kind: str, kwargs: dict[str, object], level: int, scoring: bool) -> None:
    points = None if kind in ("STUDY_SESSION", "SELF_ASSESSMENT") else 80
    (r,) = rows_for(assessments=[assessment(kind, points, **kwargs)])
    assert (r.level, r.is_scoring) == (level, scoring)


def test_pattern_drill_levels() -> None:
    drill = assessment(
        "PATTERN_DRILL",
        skill="dsa.pattern_recognition",
        timed=True,
        time_limit_seconds=480,
        time_seconds=400,
        followup_points=80,
        skills=(AssessmentSkillInput("dsa.pattern_recognition", 80), AssessmentSkillInput("s.x", 100)),
    )
    rows = by_skill(rows_for(assessments=[drill]))
    assert (rows["dsa.pattern_recognition"].level, rows["s.x"].level) == (5, 1)


def test_self_mock_outcome_is_capped_at_80() -> None:
    mock = MockRoundObservation(
        id=5,
        occurred_on=date(2026, 10, 30),
        occurred_at=datetime(2026, 10, 30, 9, tzinfo=UTC),
        source="SELF",
        round_type="DSA",
        skills=(MockRoundSkillInput("s.x", 95), MockRoundSkillInput("s.y", 40, True)),
    )
    rows = by_skill(rows_for(mocks=[mock]))
    assert (rows["s.x"].level, rows["s.x"].outcome_points) == (7, 80)
    assert rows["s.y"].is_weakness and rows["s.y"].outcome_points == 40


def test_unknown_skills_are_dropped_and_order_is_deterministic() -> None:
    attempts = [
        attempt(
            i,
            problem_id=i,
            day=date(2026, 10, 1) + timedelta(days=i),
            mappings=(("s.x", 10000), ("not.in.catalog", 5000)),
        )
        for i in range(1, 8)
    ]
    expected = rows_for(*attempts)
    assert all(r.skill in SKILLS for r in expected)
    for seed in range(3):
        shuffled = attempts[:]
        random.Random(seed).shuffle(shuffled)
        assert rows_for(*shuffled) == expected
