"""D-087: optional communication skills (``comm.*``) are isolated from technical readiness and tracks.

They carry component ``coding`` only because every skill needs one. These tests prove that practising them
can neither satisfy a technical component's recency gate (G8) nor count as DSA/coding track minutes, while
the minutes still count in the totals and per skill."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain.evidence.model import EvidenceRow
from app.domain.mentor.practice import PracticeObservation, summarize_practice, summarize_week
from app.domain.readiness.engine import recent_passing_components
from tests.golden.harness import background, given, graph, plan, profile, skills_where, summary

AS_OF = date(2026, 11, 2)


def evidence(
    skill: str, points: int = 80, on: date = date(2026, 10, 30), scoring: bool = True
) -> EvidenceRow:
    return EvidenceRow(
        source_type="ASSESSMENT",
        source_id=1,
        skill=skill,
        rule="ASSESSMENT",
        level=3,
        outcome_points=points,
        is_scoring=scoring,
        observed_on=on,
        observed_at=datetime(on.year, on.month, on.day, 9, tzinfo=UTC),
        difficulty_bp=10000,
        mapping_bp=10000,
        source_key="content:x",
        kind="CONCEPT_EXPLAIN",
    )


# --------------------------------------------------------------------------------------------------- G8


def test_communication_practice_cannot_satisfy_g8_for_any_technical_component() -> None:
    g = graph()
    assert g.skills["comm.speak_1m"].component == "coding"  # why the isolation is needed
    assert recent_passing_components([evidence("comm.speak_1m")], g, AS_OF, 21) == set()
    assert (
        recent_passing_components(
            [evidence(s) for s in graph().skills if s.startswith("comm.")], g, AS_OF, 21
        )
        == set()
    )


def test_g8_is_unchanged_for_every_other_skill() -> None:
    g = graph()
    assert recent_passing_components([evidence("python.core_syntax")], g, AS_OF, 21) == {"coding"}
    assert recent_passing_components([evidence("db.indexing")], g, AS_OF, 21) == {"cs"}
    # communication.* (STAR, follow-ups) is a required behavioral family and still counts for behavioral
    assert recent_passing_components([evidence("communication.structured_answers")], g, AS_OF, 21) == {
        "behavioral"
    }
    mixed = [
        evidence("comm.speak_1m"),
        evidence("python.core_syntax", points=59),
        evidence("db.indexing", on=date(2026, 9, 1)),
    ]
    assert recent_passing_components(mixed, g, AS_OF, 21) == set()  # 59 < 60, and 62 days old


# ------------------------------------------------------------------------------------------ track minutes


def obs_technical() -> list[PracticeObservation]:
    return [
        PracticeObservation(date(2026, 11, 1), ("graph.traversal",), time_seconds=1800),
        PracticeObservation(date(2026, 10, 30), ("db.indexing",), study_minutes=40, is_study=True),
    ]


def obs_communication() -> list[PracticeObservation]:
    return [
        PracticeObservation(date(2026, 11, 1), ("comm.speak_1m",), time_seconds=1200),
        PracticeObservation(date(2026, 10, 31), ("comm.explain_code", "comm.speak_1m"), study_minutes=30),
        PracticeObservation(date(2026, 10, 31), ("comm.status_update",), plan_item_minutes=15, is_study=True),
    ]


def test_communication_minutes_count_in_totals_and_per_skill_but_not_in_any_track() -> None:
    base = summarize_practice(obs_technical(), AS_OF, graph(), profile())
    both = summarize_practice(obs_technical() + obs_communication(), AS_OF, graph(), profile())
    assert both.track_minutes_7d == base.track_minutes_7d  # dsa_coding, cs, ... all unchanged
    assert both.track_minutes_7d["dsa_coding"] == 30 and both.track_minutes_7d["cs"] == 40
    assert both.total_minutes_14d == base.total_minutes_14d + 20 + 30 + 15
    assert both.skill_minutes_7d["comm.speak_1m"] > 0 and both.skill_minutes_7d["comm.status_update"] == 15
    assert both.study_minutes_7d["comm.status_update"] == 15
    assert {
        k: v for k, v in both.skill_minutes_7d.items() if not k.startswith("comm.")
    } == base.skill_minutes_7d


def test_weekly_dsa_and_coding_minutes_are_unchanged_by_communication_practice() -> None:
    monday, wednesday = date(2026, 11, 2), date(2026, 11, 4)
    technical = [
        PracticeObservation(monday, ("graph.traversal",), time_seconds=1800),
        PracticeObservation(wednesday, ("python.core_syntax",), time_seconds=1200),
    ]
    spoken = [
        PracticeObservation(monday, ("comm.speak_1m",), time_seconds=3600),
        PracticeObservation(wednesday, ("comm.explain_bug_root_cause",), study_minutes=25),
    ]
    base = summarize_week(technical, monday, wednesday, graph(), profile())
    both = summarize_week(technical + spoken, monday, wednesday, graph(), profile())
    assert both.track_minutes == base.track_minutes and both.track_minutes["dsa_coding"] == 50
    assert both.total_minutes == base.total_minutes + 60 + 25  # still real practice time
    assert both.active_days == 2


def test_non_communication_attribution_is_exactly_as_before() -> None:
    obs = [
        PracticeObservation(date(2026, 11, 1), ("graph.traversal", "python.core_syntax"), time_seconds=1801),
        PracticeObservation(date(2026, 11, 1), ("communication.structured_answers",), study_minutes=20),
    ]
    s = summarize_practice(obs, AS_OF, graph(), profile())
    assert s.track_minutes_7d["dsa_coding"] == 30  # both coding-component skills still count
    assert s.track_minutes_7d["behavioral_project"] == 20  # communication.* (required) still counts


# ------------------------------------------------------------------------------------- track-floor boost


def test_communication_practice_cannot_change_the_dsa_track_floor_boost() -> None:
    """Weak DSA and little DSA time earn the track-floor boost; spoken practice must not remove it."""

    def todays_plan(observations: list[PracticeObservation]):
        w = background()
        for key in skills_where(component="dsa"):
            w.set(given(key, 3, 50, "MEDIUM"))
        w.track_minutes = summarize_practice(observations, w.as_of, graph(), profile()).track_minutes_7d
        return plan(w)

    technical = [PracticeObservation(date(2026, 11, 1), ("graph.traversal",), time_seconds=1800)]
    spoken = [
        PracticeObservation(date(2026, 11, 1), ("comm.speak_1m",), time_seconds=60 * 90)
    ]  # 90 minutes of speaking
    alone = todays_plan(technical)
    with_speaking = todays_plan(technical + spoken)
    assert summary(alone) == summary(with_speaking)
    assert [i.reason_codes for i in alone.items] == [i.reason_codes for i in with_speaking.items]
    assert any("TRACK_FLOOR" in i.reason_codes for i in with_speaking.items)  # the boost is still there
