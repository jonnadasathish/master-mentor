"""REVISION_ENGINE §3-§8 transitions and replay rules (pure)."""

from __future__ import annotations

import random
from datetime import UTC, date, datetime

import pytest

from app.domain.profile.model import SkillGraph, SkillSpec
from app.domain.revision.engine import (
    initial_index,
    project_revision_items,
    review_outcome,
    revision_cap,
    schedule_revision,
    skill_item_type,
)
from app.domain.revision.model import RevisionAction, RevisionItem, RevisionObservation, RowFact
from app.domain.rulesets import v1

D = date(2026, 10, 1)


def spec(key: str, component: str = "cs", tier: str = "T2", is_pattern: bool = False) -> SkillSpec:
    return SkillSpec(key, component, "g", is_pattern, tier, 75, 75, 55, True, ())


GRAPH = SkillGraph.build(
    [spec("db.indexing", tier="T1"), spec("db.extra", tier="T3")], ["db.indexing", "db.extra"]
)


def it(
    index: int = 0,
    ladder: str = "STANDARD",
    state: str = "ACTIVE",
    lapses: int = 0,
    skill: str = "db.indexing",
) -> RevisionItem:
    return RevisionItem(
        f"CS:{skill}", "CS", skill, skill, ladder, state, None, index, D, lapses, False, D, None, 10
    )


@pytest.mark.parametrize(
    ("points", "ratio", "index"),
    [(0, None, 0), (49, None, 0), (50, None, 1), (89, None, 1), (90, None, 2), (100, 13000, 1)],
)
def test_initial_index(points: int, ratio: int | None, index: int) -> None:
    assert initial_index(points, ratio, v1) == index


def test_pass_climbs_the_standard_ladder_then_graduates_with_maintenance_for_t1_t2() -> None:
    item, day = it(), D
    dues = []
    for _ in range(6):
        item = schedule_revision(item, "PASS", day, GRAPH.skills["db.indexing"], v1)
        dues.append((item.state, item.interval_index, (item.due_date - day).days if item.due_date else None))
        day = item.due_date or day
    assert dues == [
        ("ACTIVE", 1, 3),
        ("ACTIVE", 2, 7),
        ("ACTIVE", 3, 14),
        ("ACTIVE", 4, 30),
        ("ACTIVE", 5, 60),
        ("GRADUATED", 5, 120),
    ]
    t3 = schedule_revision(it(index=5, skill="db.extra"), "PASS", D, GRAPH.skills["db.extra"], v1)
    assert (t3.state, t3.due_date) == ("GRADUATED", None)  # T3/T4: no maintenance


def test_partial_keeps_index_and_fail_resets_with_lapse_until_leech() -> None:
    partial = schedule_revision(it(index=3), "PARTIAL", D, None, v1)
    assert (partial.interval_index, (partial.due_date - D).days) == (3, 14)
    failed = schedule_revision(it(index=3, lapses=1), "FAIL", D, None, v1)
    assert (failed.interval_index, failed.lapses, failed.needs_reinforcement, (failed.due_date - D).days) == (
        0,
        2,
        True,
        1,
    )
    leech = schedule_revision(it(lapses=2), "FAIL", D, None, v1)
    assert (leech.state, leech.suspend_reason, leech.lapses) == ("SUSPENDED", "LEECH", 3)


def test_mockw_ladder_and_maintenance_outcomes() -> None:
    m = it(ladder="MOCKW")
    assert [(schedule_revision(m, "PASS", D, None, v1).due_date - D).days] == [5]
    assert (schedule_revision(it(index=2, ladder="MOCKW"), "PASS", D, None, v1).state) == "GRADUATED"
    graduated = it(state="GRADUATED", index=5)
    assert (schedule_revision(graduated, "PASS", D, None, v1).due_date - D).days == 120
    assert (schedule_revision(graduated, "PARTIAL", D, None, v1).due_date - D).days == 60
    back = schedule_revision(graduated, "FAIL", D, None, v1)
    assert (back.state, back.interval_index, back.lapses, (back.due_date - D).days) == ("ACTIVE", 2, 1, 7)


def obs(
    day: date, outcome: str = "PASS", hints: int = 0, seconds: int | None = 600, key: str | None = None
) -> RevisionObservation:
    return RevisionObservation(
        "ATTEMPT",
        day.toordinal(),
        day,
        datetime(day.year, day.month, day.day, 6, tzinfo=UTC),
        (),
        key,
        None,
        outcome,
        hints,
        False,
        seconds,
    )


def test_problem_review_outcomes() -> None:
    p = RevisionItem(
        "PROBLEM:1", "PROBLEM", "s", "1", "STANDARD", "ACTIVE", None, 1, D, 0, False, D, None, 25
    )
    assert review_outcome(p, obs(D), v1) == "PASS"
    assert review_outcome(p, obs(D, seconds=26 * 60), v1) == "PARTIAL"  # slower than item minutes
    assert review_outcome(p, obs(D, hints=1), v1) == "PARTIAL"
    assert review_outcome(p, obs(D, outcome="FAIL"), v1) == "FAIL"


def test_skill_item_types_follow_section_2() -> None:
    assert skill_item_type(spec("graph.traversal", "dsa", is_pattern=True)) == "PATTERN"
    assert skill_item_type(spec("recursion.fundamentals", "dsa")) == "CONCEPT"
    assert skill_item_type(spec("dsa.pattern_recognition", "dsa")) is None
    assert skill_item_type(spec("python.core_syntax", "coding")) == "CONCEPT"
    assert skill_item_type(spec("execution.think_aloud", "coding")) is None
    assert skill_item_type(spec("lld.machine_coding", "lld")) is None
    assert skill_item_type(spec("sd.caching", "system_design")) == "SD"
    assert skill_item_type(spec("comm.speak_1m", "coding", tier="T4")) == "CONCEPT"  # D-087
    assert skill_item_type(spec("communication.structured_answers", "behavioral")) is None  # stories: STAR


def test_manual_suspend_and_resume_replay_and_unlinked_practice_does_not_review() -> None:
    created = RevisionObservation(
        "ASSESSMENT", 1, D, datetime(2026, 10, 1, 6, tzinfo=UTC), (RowFact("db.indexing", 3, 95, True),)
    )
    unlinked = RevisionObservation(
        "ASSESSMENT",
        2,
        date(2026, 10, 3),
        datetime(2026, 10, 3, 6, tzinfo=UTC),
        (RowFact("db.indexing", 3, 10, True),),
    )
    actions = [
        RevisionAction(
            1, "CS:db.indexing", "SUSPEND", "MANUAL", date(2026, 10, 4), datetime(2026, 10, 4, 6, tzinfo=UTC)
        ),
        RevisionAction(
            2, "CS:db.indexing", "RESUME", "MANUAL", date(2026, 10, 9), datetime(2026, 10, 9, 6, tzinfo=UTC)
        ),
    ]

    def run(as_of: date, acts=actions):  # type: ignore[no-untyped-def]
        return project_revision_items(
            observations=[unlinked, created], actions=acts, graph=GRAPH, as_of_date=as_of, ruleset=v1
        )

    first = run(date(2026, 10, 3)).items["CS:db.indexing"]
    assert (first.interval_index, first.due_date, first.lapses) == (
        2,
        date(2026, 10, 8),
        0,
    )  # ad-hoc FAIL ignored
    assert run(date(2026, 10, 5)).items["CS:db.indexing"].state == "SUSPENDED"
    resumed = run(date(2026, 10, 10)).items["CS:db.indexing"]
    assert (resumed.state, resumed.due_date) == ("ACTIVE", date(2026, 10, 9))
    shuffled = actions[:]
    random.Random(4).shuffle(shuffled)
    assert run(date(2026, 10, 10), shuffled) == run(date(2026, 10, 10))


def test_cap() -> None:
    assert (revision_cap(90, v1), revision_cap(20, v1), revision_cap(180, v1)) == (36, 15, 72)


def test_communication_revision_needs_real_practice_and_creates_one_item_per_skill() -> None:
    """D-087: one CONCEPT item per communication skill, only from a scoring row of level >= 2."""
    graph = SkillGraph.build([spec("comm.speak_1m", "coding", tier="T4")], ["comm.speak_1m"])

    def project(rows: tuple[RowFact, ...], source_id: int = 1) -> dict[str, RevisionItem]:
        observation = RevisionObservation(
            "ASSESSMENT", source_id, D, datetime(2026, 10, 1, 6, tzinfo=UTC), rows
        )
        return dict(
            project_revision_items(
                observations=[observation], actions=[], graph=graph, as_of_date=D, ruleset=v1
            ).items
        )

    assert project((RowFact("comm.speak_1m", 0, None, False),)) == {}  # lesson or self-report: no item
    assert project((RowFact("comm.speak_1m", 1, 80, True),)) == {}  # closed-book recall only
    items = project((RowFact("comm.speak_1m", 3, 80, True),))
    assert list(items) == ["CONCEPT:comm.speak_1m"] and items["CONCEPT:comm.speak_1m"].item_type == "CONCEPT"
