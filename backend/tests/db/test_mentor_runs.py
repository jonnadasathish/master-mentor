"""Mentor runs against the real schema: determinism across wall-clock time, dev reset safety."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli import devtools
from app.domain.clock import FixedClock
from app.models import Assessment, AuditLog, MentorRun, ProblemAttempt, Skill, SkillState
from app.models.system import MentorRunTrigger
from app.schemas.activity import ProblemAttemptInput
from app.services.activity_service import ActivityService
from app.services.mentor_service import MentorService
from app.services.seed_service import SeedLoader
from tests.catalog_helpers import SEED_DIR

pytestmark = pytest.mark.db
CLOCK = FixedClock(datetime(2026, 10, 4, 12, 0, tzinfo=UTC))


@pytest.fixture
def populated(catalog_session: Session) -> Session:
    SeedLoader(catalog_session, CLOCK).load(SEED_DIR)
    activity = ActivityService(catalog_session, CLOCK)
    for problem_id, outcome, day in [(27, "FAIL", 1), (27, "PASS", 2), (31, "PARTIAL", 3), (1, "PASS", 3)]:
        activity.record_attempt(
            ProblemAttemptInput(
                problem_id=problem_id,
                outcome=outcome,
                time_seconds=1200,
                attempted_at=datetime(2026, 10, day, 6, 0, tzinfo=UTC),
            )
        )
    return catalog_session


def states(session: Session) -> list[tuple[object, ...]]:
    return [
        (s.skill_id, s.score, s.level, s.confidence, s.effective_score, s.considered_evidence_json)
        for s in session.scalars(select(SkillState).order_by(SkillState.skill_id))
    ]


def test_same_as_of_date_gives_same_result_at_any_wall_clock_time(populated: Session) -> None:
    as_of = date(2026, 10, 4)
    first = MentorService(populated, CLOCK).recalculate(MentorRunTrigger.REBUILD, as_of=as_of)
    snapshot = states(populated)
    later = FixedClock(datetime(2031, 1, 1, 3, 0, tzinfo=UTC))  # wall clock years later
    second = MentorService(populated, later).recalculate(MentorRunTrigger.REBUILD, as_of=as_of)
    assert first.input_hash == second.input_hash
    assert states(populated) == snapshot
    assert first.skill_deltas and second.skill_deltas == []  # nothing changed the second time


def test_as_of_date_moves_recency_not_history(populated: Session) -> None:
    early = MentorService(populated, CLOCK).recalculate(MentorRunTrigger.REBUILD, as_of=date(2026, 10, 1))
    late = MentorService(populated, CLOCK).recalculate(MentorRunTrigger.REBUILD, as_of=date(2026, 10, 4))
    assert early.evidence_rows == late.evidence_rows  # evidence is derived from observations only
    assert sum(1 for s in early.states.values() if s.assessed) < sum(
        1 for s in late.states.values() if s.assessed
    )


def test_dev_reset_requires_confirmation_and_keeps_the_catalog(
    populated: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    MentorService(populated, CLOCK).recalculate(MentorRunTrigger.REBUILD)
    assert devtools.main(["reset-prep"]) == 2
    assert "refused" in capsys.readouterr().err
    assert populated.scalar(select(func.count()).select_from(ProblemAttempt)) == 4

    deleted = devtools.reset_prep(populated)
    assert deleted["problem_attempts"] == 4 and deleted["skill_states"] > 0
    for model in (ProblemAttempt, Assessment, SkillState, MentorRun):
        assert populated.scalar(select(func.count()).select_from(model)) == 0
    assert populated.scalar(select(func.count()).select_from(Skill)) == 133
    assert populated.scalar(select(AuditLog.action).where(AuditLog.action == "DEV_RESET")) == "DEV_RESET"


def test_s01_cold_start_all_unassessed_and_calibrating(catalog_session: Session) -> None:
    """S01 skill-state part: no observations -> 133 UNASSESSED, 0/123 required, battery at B01."""
    from app.services.skill_service import SkillService

    SeedLoader(catalog_session, CLOCK).load(SEED_DIR)
    result = MentorService(catalog_session, CLOCK).recalculate(MentorRunTrigger.GOAL, as_of=date(2026, 11, 2))
    assert len(result.states) == 133
    assert all(
        s.label == "UNASSESSED" and s.score is None and s.confidence == "NONE" for s in result.states.values()
    )
    status = SkillService(catalog_session, CLOCK).calibration()
    assert (status.required, status.assessed_required, status.next_item) == (123, 0, "M0-B01")
    assert status.calibration_mode is True and status.battery_done == 0
