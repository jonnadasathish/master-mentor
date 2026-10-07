"""D-087: optional communication practice inside the existing deterministic planner.

Communication competes through the ordinary gap ranking and the ordinary mission templates. It may use
time that technical work did not need, but it never displaces, reorders or changes technical work."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.rulesets import v1
from tests.golden.harness import World, background, given, plan, summary, unassessed

BUILD = date(2027, 6, 28)  # far from the target: phase BUILD, where T4 skills are not parked
CONSOLIDATE = date(2027, 1, 11)
WEAK_COMM = ("comm.speak_30s", "comm.sentence_formation")


def world(budget: int = 90, target: date = BUILD, *, technical: bool = True, spoken: bool = False) -> World:
    w = background(target_date=target, budget=budget)
    if technical:
        w.set(given("two_pointers.core", 3, 50, "MEDIUM", effective=40))
    if spoken:
        w.set(given("comm.sentence_formation", 3, 70, "MEDIUM"))
        w.set(given("comm.speak_30s", 1, 5, "LOW", effective=0))
    return w


def technical_items(p) -> list[tuple[object, ...]]:
    return [
        (i.candidate_key, i.template_key, i.stage, i.minutes, i.score)
        for i in p.items
        if not (i.skill or "").startswith("comm.")
    ]


@pytest.mark.parametrize("budget", [30, 45, 50, 60, 75, 80, 85, 89, 90, 120])
def test_technical_work_is_identical_with_or_without_a_weak_communication_skill(budget: int) -> None:
    alone = plan(world(budget))
    with_speaking = plan(world(budget, spoken=True))
    if budget >= 45:  # below that the technical mission does not fit the day at all
        assert technical_items(with_speaking) == technical_items(alone)
    assert with_speaking.allocated_minutes <= budget
    comm = [i for i in with_speaking.items if (i.skill or "").startswith("comm.")]
    assert all(
        i.template_key and i.template_key.startswith("coding.comm_") for i in comm
    )  # never coding problems


def test_communication_only_uses_time_the_technical_plan_left_unused() -> None:
    p = plan(world(90, spoken=True))
    assert [i.candidate_key for i in p.items] == [
        "GAP:two_pointers.core",
        "FOLLOW:two_pointers.core",
        "GAP:comm.speak_30s",
    ]
    tight = plan(world(85, spoken=True))
    assert "FOLLOW:two_pointers.core" in [i.candidate_key for i in tight.items]  # not displaced by 10 minutes
    assert {d.key: d.reason for d in tight.dropped}["GAP:comm.speak_30s"] == "BUDGET"


def test_a_weak_communication_skill_is_a_real_candidate_when_nothing_technical_needs_the_day() -> None:
    p = plan(world(technical=False, spoken=True))
    assert [(i.candidate_key, i.template_key, i.stage) for i in p.items][0] == (
        "GAP:comm.speak_30s",
        "coding.comm_guided",
        "GUIDED",
    )


def test_an_unassessed_communication_root_is_diagnosed_with_a_communication_mission() -> None:
    w = world(technical=False)
    w.set(unassessed("comm.sentence_formation"))
    p = plan(w)
    assert [(i.candidate_key, i.template_key) for i in p.items] == [
        ("DIAG:comm.sentence_formation", "coding.comm_diagnose")
    ]


def test_communication_never_outranks_required_technical_gaps() -> None:
    w = world(spoken=True)
    w.set(given("binary_search.boundaries", 2, 30, "LOW", effective=20))
    p = plan(w)
    keys = [i.candidate_key for i in p.items]
    assert keys[0].startswith("GAP:") and not keys[0].startswith("GAP:comm.")
    assert all(not k.startswith("GAP:comm.") for k in keys[:2])
    assert len(set(keys)) == len(keys)  # no duplicate missions


def test_many_weak_communication_skills_still_respect_the_item_cap_and_focus_limit() -> None:
    w = world(120, technical=False, spoken=True)
    for key in (
        "comm.speak_1m",
        "comm.filler_reduction",
        "comm.status_update",
        "comm.explain_code",
        "comm.chat_message",
    ):
        w.set(given(key, 1, 5, "LOW", effective=0))
    p = plan(w)
    gap_skills = {i.skill for i in p.items if i.candidate_type == "GAP"}
    assert len(p.items) <= v1.MAX_PLAN_ITEMS and len(gap_skills) <= v1.FOCUS_LIMIT_SKILLS
    assert p.allocated_minutes <= 120


def test_the_plan_is_deterministic_with_communication_in_it() -> None:
    assert summary(plan(world(spoken=True))) == summary(plan(world(spoken=True)))


def test_after_the_build_phase_parked_communication_is_neither_planned_nor_listed_to_stop() -> None:
    p = plan(world(target=CONSOLIDATE, spoken=True))
    assert not any((i.skill or "").startswith("comm.") for i in p.items)
    assert not any(s.skill.startswith("comm.") for s in p.stop_list)


def test_adding_communication_evidence_never_changes_technical_recommendations() -> None:
    baseline = plan(world(spoken=False))
    for states in (
        {"comm.sentence_formation": (3, 70, "MEDIUM"), "comm.speak_30s": (2, 55, "MEDIUM")},
        {
            "comm.sentence_formation": (4, 80, "HIGH"),
            "comm.speak_30s": (4, 80, "HIGH"),
            "comm.speak_1m": (3, 60, "MEDIUM"),
        },
    ):
        w = world(spoken=False)
        for key, (level, score, confidence) in states.items():
            w.set(given(key, level, score, confidence))
        assert technical_items(plan(w)) == technical_items(baseline)
