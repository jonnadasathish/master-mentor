"""Future-compatibility: the evidence engine's raw-observation queries are answerable and index-backed."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.domain.clock import FixedClock
from app.repositories.activity_repository import ActivityRepository
from app.schemas.activity import ProblemAttemptInput
from app.services.activity_service import ActivityService
from app.services.seed_service import SeedLoader
from tests.catalog_helpers import SEED_DIR

pytestmark = pytest.mark.db
CLOCK = FixedClock(datetime(2026, 10, 4, 12, 0, tzinfo=UTC))

SKILL_QUERY = """
SELECT a.id, a.attempted_on, a.outcome, a.time_seconds, a.hints_used, a.self_rating_before,
       a.explanation_score, a.complexity_correct, p.difficulty, ps.mapping_weight_bp
FROM skills s
JOIN problem_skills ps ON ps.skill_id = s.id
JOIN problem_attempts a ON a.problem_id = ps.problem_id
JOIN problems p ON p.id = a.problem_id
WHERE s.skill_key = :skill AND a.attempted_on BETWEEN :d1 AND :d2
"""


@pytest.fixture
def populated(catalog_session: Session) -> Session:
    SeedLoader(catalog_session, CLOCK).load(SEED_DIR)
    service = ActivityService(catalog_session, CLOCK)
    for problem_id, outcome, day in [(27, "FAIL", 1), (27, "PASS", 2), (31, "PARTIAL", 3), (1, "PASS", 3)]:
        service.record_attempt(
            ProblemAttemptInput(
                problem_id=problem_id,
                outcome=outcome,
                time_seconds=1200,
                hints_used=1,
                mistakes=["WRONG_PATTERN"] if outcome == "FAIL" else [],
                self_rating_before=3,
                explanation_score=6,
                complexity_correct=True,
                attempted_at=datetime(2026, 10, day, 6, 0, tzinfo=UTC),
            )
        )
    return catalog_session


def test_skill_observations_carry_everything_the_evidence_engine_needs(populated: Session) -> None:
    rows = ActivityRepository(populated).attempts(skill_key="graph.traversal", ascending=True)
    assert [(r.attempt.outcome, r.problem.difficulty, r.skill_mapping_bp) for r in rows] == [
        ("FAIL", "MEDIUM", 10000),
        ("PASS", "MEDIUM", 10000),
        ("PARTIAL", "MEDIUM", 5000),
    ]
    first = rows[0]
    assert first.mistakes == ("WRONG_PATTERN",)
    assert (first.attempt.time_seconds, first.attempt.hints_used, first.attempt.self_rating_before) == (
        1200,
        1,
        3,
    )
    assert (first.attempt.explanation_score, first.attempt.complexity_correct) == (6, True)
    assert first.attempt.attempted_on == date(2026, 10, 1)


def test_problem_user_and_date_range_queries(populated: Session) -> None:
    repo = ActivityRepository(populated)
    assert len(repo.attempts(problem_id=27)) == 2
    assert len(repo.attempts()) == 4  # single user: all observations
    window = repo.attempts(date_from=date(2026, 10, 2), date_to=date(2026, 10, 2))
    assert [r.attempt.outcome for r in window] == ["PASS"]


def test_skill_date_query_uses_indexes(populated: Session, catalog_engine: Engine) -> None:
    with catalog_engine.connect() as connection:
        plan = (
            connection.execute(
                text("EXPLAIN " + SKILL_QUERY),
                {"skill": "graph.traversal", "d1": "2026-09-01", "d2": "2026-10-31"},
            )
            .mappings()
            .all()
        )
    by_table = {row["table"]: row for row in plan}
    assert by_table["a"]["key"] is not None, plan  # problem_attempts reached through an index
    assert by_table["ps"]["key"] is not None, plan
    assert by_table["s"]["key"] is not None, plan
