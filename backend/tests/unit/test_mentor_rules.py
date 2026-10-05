"""MENTOR_ENGINE §4-§5 helpers: practice minutes, roadmap order, stage step-down (pure)."""

from __future__ import annotations

from datetime import date

from app.domain.mentor.planner import step_down
from app.domain.mentor.practice import PracticeObservation, split_minutes, summarize_practice
from app.domain.mentor.roadmap import current_milestones, learn_allowed_by_roadmap
from app.domain.rulesets import v1
from tests.golden.harness import background, catalog, declared_unknown, graph, profile

AS_OF = date(2026, 11, 2)


def test_minutes_come_from_time_then_study_then_plan_item_and_split_with_remainder_first() -> None:
    o = PracticeObservation(AS_OF, ("b.skill", "a.skill", "c.skill"), time_seconds=11 * 60)
    assert split_minutes(o) == {"a.skill": 5, "b.skill": 3, "c.skill": 3}
    assert split_minutes(PracticeObservation(AS_OF, ("x",), study_minutes=20)) == {"x": 20}
    assert split_minutes(PracticeObservation(AS_OF, ("x",), plan_item_minutes=35)) == {"x": 35}


def test_track_minutes_cover_the_previous_seven_days_only() -> None:
    obs = [
        PracticeObservation(date(2026, 11, 1), ("graph.traversal",), time_seconds=1800),  # 1 day ago
        PracticeObservation(date(2026, 10, 26), ("db.indexing",), study_minutes=40, is_study=True),  # 7 days
        PracticeObservation(date(2026, 10, 25), ("db.indexing",), study_minutes=99),  # 8 days: 14d only
        PracticeObservation(AS_OF, ("graph.traversal",), time_seconds=6000),  # today: not history yet
    ]
    s = summarize_practice(obs, AS_OF, graph(), profile())
    assert (s.track_minutes_7d["dsa_coding"], s.track_minutes_7d["cs"]) == (30, 40)
    assert s.study_minutes_7d == {"db.indexing": 40} and s.skill_minutes_14d["db.indexing"] == 139
    assert s.total_minutes_14d == 169


def test_roadmap_current_milestone_and_learn_order() -> None:
    world = background()
    world.set(declared_unknown("trie.core"))  # DSA-3 becomes incomplete
    current = current_milestones(catalog().milestones, world.states, graph(), _facts())
    assert current["dsa_coding"] is not None and current["dsa_coding"].key == "DSA-3"
    assert learn_allowed_by_roadmap("trie.core", catalog().milestones, current)
    later = next(m for m in catalog().milestones if m.track == "dsa_coding" and m.position == 4)
    assert not learn_allowed_by_roadmap(later.skills[0], catalog().milestones, current)


def test_stage_step_down_ladder() -> None:
    assert [
        step_down(s, v1) for s in ("LEARN", "GUIDED", "TIMED", "PATTERN_DRILL", "THINK_ALOUD", "REINFORCE")
    ] == [
        "LEARN",
        "RECALL",
        "INDEPENDENT",
        "RECALL",
        "GUIDED",
        "RECALL",
    ]


def _facts():  # type: ignore[no-untyped-def]
    from app.domain.mentor.model import ExitFacts

    return ExitFacts()
