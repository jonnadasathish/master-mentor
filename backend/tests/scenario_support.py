"""Builders shared by domain/scenario tests (SCENARIOS.md §0 conventions)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from itertools import count

from app.domain.evidence.model import AttemptObservation, EvidenceRow

AS_OF = date(2026, 11, 2)  # F0
_ids = count(1)


def row(
    level: int,
    points: int,
    age: int,
    source: str | None = None,
    *,
    skill: str = "s.x",
    difficulty_bp: int = 10000,
    mapping_bp: int = 10000,
    as_of: date = AS_OF,
    **extra: object,
) -> EvidenceRow:
    """SCENARIOS.md ``row(level, points, age_days, source)``: MEDIUM difficulty, primary mapping."""
    observed = as_of - timedelta(days=age)
    source_id = next(_ids)
    values: dict[str, object] = {
        "source_type": "MOCK_ROUND" if level == 7 else "ATTEMPT",
        "rule": "MOCK" if level == 7 else "MAPPED",
        "is_scoring": True,
    }
    values.update(extra)
    return EvidenceRow(
        source_id=source_id,
        skill=skill,
        level=level,
        outcome_points=points,
        observed_on=observed,
        observed_at=datetime(observed.year, observed.month, observed.day, 6, tzinfo=UTC),
        difficulty_bp=difficulty_bp,
        mapping_bp=mapping_bp,
        source_key=source or f"src:{source_id}",
        **values,  # type: ignore[arg-type]
    )


def attempt(
    id: int,
    *,
    problem_id: int = 1,
    day: date = date(2026, 10, 30),
    outcome: str = "PASS",
    difficulty: str = "MEDIUM",
    mappings: tuple[tuple[str, int], ...] = (("s.x", 10000),),
    **overrides: object,
) -> AttemptObservation:
    values: dict[str, object] = dict(
        id=id,
        problem_id=problem_id,
        attempted_on=day,
        attempted_at=datetime(day.year, day.month, day.day, 6, tzinfo=UTC) + timedelta(minutes=id),
        outcome=outcome,
        seen_elsewhere=False,
        hints_used=0,
        solution_viewed=False,
        pattern_identified=None,
        timed=False,
        time_limit_seconds=None,
        time_seconds=None,
        explanation_score=None,
        complexity_correct=None,
        followup_solved=None,
        execution_rubric=None,
        mistakes=(),
        self_rating_before=None,
        difficulty=difficulty,
        expected_minutes=None,
        mappings=mappings,
    )
    values.update(overrides)
    return AttemptObservation(**values)  # type: ignore[arg-type]
