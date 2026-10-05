"""Final deterministic replay audit (master prompt): repeat, change wall-clock time, change input order.

Every derived output is compared by natural keys: skill states, gaps, revision items, readiness, plan."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.clock import FixedClock
from app.models.system import MentorRunTrigger
from app.schemas.activity import ProblemAttemptInput
from app.schemas.assessment import AssessmentInput
from app.schemas.profile import GoalInput
from app.services.activity_service import ActivityService
from app.services.assessment_service import AssessmentService
from app.services.mentor_service import MentorService
from app.services.plan_service import PlanService
from app.services.profile_service import ProfileService
from app.services.seed_service import SeedLoader
from tests.catalog_helpers import SEED_DIR, clear_catalog

pytestmark = pytest.mark.db
AS_OF = date(2026, 10, 20)
NOW = FixedClock(datetime(2026, 10, 20, 6, 0, tzinfo=UTC))
LATER = FixedClock(datetime(2031, 3, 1, 23, 0, tzinfo=UTC))

ATTEMPTS = [
    dict(problem_id=1, outcome="PASS", time_seconds=900, attempted_at="2026-10-01T06:00:00Z"),
    dict(
        problem_id=27,
        outcome="FAIL",
        time_seconds=1800,
        mistakes=["WRONG_PATTERN"],
        pattern_identified=False,
        attempted_at="2026-10-03T06:00:00Z",
    ),
    dict(
        problem_id=6, outcome="PARTIAL", time_seconds=2000, hints_used=1, attempted_at="2026-10-08T06:00:00Z"
    ),
    dict(
        problem_id=27,
        outcome="PASS",
        time_seconds=1500,
        timed=True,
        time_limit_seconds=1800,
        explanation_score=8,
        complexity_correct=True,
        attempted_at="2026-10-15T06:00:00Z",
    ),
]
ASSESSMENTS = [
    dict(
        kind="CONCEPT_EXPLAIN",
        source_key="prompt:a",
        skills=[{"skill": "db.indexing", "outcome_points": 85}],
        observed_at="2026-10-05T06:00:00Z",
    ),
    dict(
        kind="RECALL_QUIZ",
        source_key="prompt:b",
        skills=[{"skill": "os.processes_threads", "outcome_points": 40}],
        observed_at="2026-10-10T06:00:00Z",
    ),
]


def populate(session: Session, reverse: bool) -> None:
    SeedLoader(session, NOW).load(SEED_DIR)
    ProfileService(session, FixedClock(datetime(2026, 9, 1, tzinfo=UTC)), "v1").create_goal(
        GoalInput(target_date=date(2027, 6, 28))
    )
    attempts = list(reversed(ATTEMPTS)) if reverse else ATTEMPTS
    assessments = list(reversed(ASSESSMENTS)) if reverse else ASSESSMENTS
    for a in attempts:
        ActivityService(session, NOW).record_attempt(ProblemAttemptInput.model_validate(a))
    for s in assessments:
        AssessmentService(session, NOW).record(AssessmentInput.model_validate(s))


def snapshot(session: Session, engine: Engine, clock: FixedClock) -> dict[str, Any]:
    result = MentorService(session, clock).recalculate(MentorRunTrigger.REBUILD, as_of=AS_OF)
    queries = {
        "states": "SELECT s.skill_key, st.score, st.level, st.quality, st.confidence, st.effective_score, "
        "st.peak_score, st.label FROM skill_states st JOIN skills s ON s.id = st.skill_id "
        "ORDER BY s.skill_key",
        "gaps": "SELECT s.skill_key, g.priority, g.status, g.rank, g.primary_gap_type, g.focus_stage, "
        "g.reason_codes_json FROM gap_states g JOIN skills s ON s.id = g.skill_id ORDER BY s.skill_key",
        "revision": "SELECT item_key, state, due_date, interval_index, lapses, needs_reinforcement "
        "FROM revision_items ORDER BY item_key",
        "readiness": "SELECT state, weighted_score, blockers_json FROM readiness_snapshots "
        "WHERE snapshot_date = :d",
    }
    with engine.connect() as c:
        out: dict[str, Any] = {
            k: [tuple(r) for r in c.execute(text(q), {"d": AS_OF}).all()] for k, q in queries.items()
        }
    out["input_hash"] = result.input_hash
    plan, _ = PlanService(session, clock)._build(AS_OF, result, 90)  # noqa: SLF001 - the pure plan for as_of
    out["plan"] = [
        (i.candidate_key, i.template_key, i.stage, i.minutes, i.score, i.problem_ids) for i in plan.items
    ]
    out["message"] = plan.message.text
    return out


def test_replay_is_identical_across_repeats_wall_clock_and_input_order(catalog_engine: Engine) -> None:
    factory = sessionmaker(bind=catalog_engine, expire_on_commit=False)
    with factory() as session:
        populate(session, reverse=False)
        first = snapshot(session, catalog_engine, NOW)
        repeats = [snapshot(session, catalog_engine, NOW) for _ in range(3)]
        later = snapshot(session, catalog_engine, LATER)
    assert all(r == first for r in repeats), "repeat"
    assert later == first, "wall-clock time changed the result"
    assert first["states"] and first["plan"] and first["revision"]

    clear_catalog(catalog_engine)
    with catalog_engine.begin() as c:
        c.execute(text("DELETE FROM goals"))
    with factory() as session:
        populate(session, reverse=True)
        reordered = snapshot(session, catalog_engine, NOW)
    # input_hash identifies the exact stored rows, surrogate ids included (D-076);
    # every engine output must match.
    assert reordered["input_hash"] != first["input_hash"]
    assert {k: v for k, v in reordered.items() if k != "input_hash"} == {
        k: v for k, v in first.items() if k != "input_hash"
    }, "input order changed the result"


def synthetic_history(session: Session, days: int) -> list[date]:
    """60 local days: a goal, ~2 attempts/day over 12 problems, an assessment every 3rd day, a weekly mock."""
    SeedLoader(session, NOW).load(SEED_DIR)
    ProfileService(session, FixedClock(datetime(2026, 7, 1, tzinfo=UTC)), "v1").create_goal(
        GoalInput(target_date=date(2027, 6, 28))
    )
    problems = [1, 2, 3, 4, 6, 9, 12, 15, 16, 20, 27, 28]
    outcomes = ["PASS", "PARTIAL", "FAIL", "PASS", "PASS"]
    start = date(2026, 7, 6)
    clock = FixedClock(datetime(2026, 10, 1, tzinfo=UTC))
    for d in range(days):
        day = start.toordinal() + d
        for k in range(2):
            n = d * 2 + k
            ActivityService(session, clock).record_attempt(
                ProblemAttemptInput(
                    problem_id=problems[n % len(problems)],
                    outcome=outcomes[n % len(outcomes)],
                    time_seconds=900 + (n % 7) * 300,
                    hints_used=n % 3 // 2,
                    attempted_at=datetime.fromordinal(day).replace(hour=5 + k, tzinfo=UTC),
                )
            )
        if d % 3 == 0:
            AssessmentService(session, clock).record(
                AssessmentInput(
                    kind="CONCEPT_EXPLAIN",
                    source_key=f"prompt:p{d % 5}",
                    skills=[
                        {
                            "skill": ["db.indexing", "os.processes_threads", "network.http"][d % 3],
                            "outcome_points": 40 + d % 60,
                        }
                    ],
                    observed_at=datetime.fromordinal(day).replace(hour=12, tzinfo=UTC),
                )
            )
    return [date.fromordinal(start.toordinal() + d) for d in range(days)]


def test_sixty_day_history_rebuilds_every_daily_snapshot(catalog_engine: Engine) -> None:
    factory = sessionmaker(bind=catalog_engine, expire_on_commit=False)
    with factory() as session:
        days = synthetic_history(session, 60)
        for day in days:
            MentorService(
                session, FixedClock(datetime(day.year, day.month, day.day, 18, tzinfo=UTC))
            ).recalculate(MentorRunTrigger.OBSERVATION, as_of=day)

    skills_sql = text(
        "SELECT snapshot_date, skill_id, score, effective_score, level, confidence, priority, status "
        "FROM skill_daily_snapshots ORDER BY snapshot_date, skill_id"
    )
    readiness_sql = text(
        "SELECT snapshot_date, state, weighted_score, blockers_json FROM readiness_snapshots "
        "ORDER BY snapshot_date"
    )

    def daily() -> dict[str, list[tuple[Any, ...]]]:
        with catalog_engine.connect() as c:
            return {
                "skills": [tuple(r) for r in c.execute(skills_sql).all()],
                "readiness": [tuple(r) for r in c.execute(readiness_sql).all()],
            }

    before = daily()
    assert len({r[0] for r in before["skills"]}) == 60 and len(before["readiness"]) == 60
    with factory() as session:
        result = MentorService(session, FixedClock(datetime(2026, 9, 3, 12, tzinfo=UTC))).rebuild()
    assert result["runs"] == 60  # 59 past dates + today (2026-09-03 = the last synthetic day)
    assert daily() == before
