"""Personal roadmap classification (D-080) over real engine output (golden-harness worlds). Pure."""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.roadmap.personal import (
    BUILD,
    CONSOLIDATE,
    FOCUS_SIZE,
    MAINTAIN,
    PARKED,
    SHARPEN,
    UNMEASURED,
    build_personal_roadmap,
    roadmap_bucket,
    roadmap_changes,
    skill_health,
)
from tests.golden.harness import F0, background, declared_unknown, given, graph, unassessed


def roadmap(world):  # type: ignore[no-untyped-def]
    return build_personal_roadmap(world.gaps(), world.states, graph())


def test_a_world_at_target_has_nothing_to_build_and_everything_to_maintain() -> None:
    r = roadmap(background())
    assert r.focus_now == ()
    assert r.counts[MAINTAIN] == len(graph().skills) and r.counts[BUILD] == 0
    assert r.health_counts["strong"] == len(graph().skills)


def test_strong_skills_are_never_in_focus_or_taught_again() -> None:
    w = background()
    w.set(given("graph.traversal", 3, 51, "MEDIUM", effective=44))  # one weak skill in a strong world
    r = roadmap(w)
    keys = [i.skill_key for i in r.focus_now]
    assert "graph.traversal" in keys
    assert all(i.health != "strong" for i in r.focus_now)
    strong = {i.skill_key for i in r.bucket(MAINTAIN)}
    assert "graph.traversal" not in strong and "arrays.traversal" in strong
    assert not strong & set(keys)


def test_weak_prerequisites_are_prioritized_over_the_skills_they_block() -> None:
    w = background()
    w.set(given("recursion.fundamentals", 1, 20, "MEDIUM", effective=12))  # a prerequisite
    for dependent in graph().dependents["recursion.fundamentals"]:
        w.set(given(dependent, 1, 25, "MEDIUM", effective=18))
    r = roadmap(w)
    by = {i.skill_key: i for i in r.items}
    assert by["recursion.fundamentals"].skill_key in [i.skill_key for i in r.focus_now]
    blocked = [i for i in r.items if i.status == "BLOCKED"]
    assert blocked, "weak dependents of a weak prerequisite are blocked"
    assert all(i.bucket == BUILD and i.prerequisites for i in blocked)
    assert all(i.skill_key not in [f.skill_key for f in r.focus_now] for i in blocked)
    assert any(p.skill == "recursion.fundamentals" for p in blocked[0].prerequisites)


def test_unmeasured_skills_are_not_pretended_to_be_weak_or_strong() -> None:
    w = background()
    w.set(unassessed("heap.top_k"))
    item = {i.skill_key: i for i in roadmap(w).items}["heap.top_k"]
    assert (item.bucket, item.health) == (UNMEASURED, "unknown")


def test_a_declared_unknown_counts_as_measured_at_zero() -> None:
    w = background()
    w.set(declared_unknown("heap.top_k"))
    item = {i.skill_key: i for i in roadmap(w).items}["heap.top_k"]
    assert item.bucket == BUILD and item.score == 0 and item.health in ("critical", "developing")


def test_buckets_follow_the_engines_recommended_stage() -> None:
    w = background()
    w.set(given("graph.traversal", 3, 51, "MEDIUM", effective=44))
    gap = {g.skill_key: g for g in w.gaps().gaps}["graph.traversal"]
    state = w.states["graph.traversal"]
    expected = {
        "LEARN": BUILD,
        "DIAGNOSE": BUILD,
        "GUIDED": CONSOLIDATE,
        "INDEPENDENT": CONSOLIDATE,
        "PATTERN_DRILL": CONSOLIDATE,
        "TIMED": SHARPEN,
        "EXPLAIN": SHARPEN,
        "SIMULATE": SHARPEN,
    }
    assert gap.focus_stage in expected
    assert roadmap_bucket(gap, state) == expected[gap.focus_stage]


def test_health_is_strong_developing_critical_unknown_or_parked() -> None:
    w = background()
    w.set(given("graph.traversal", 3, 30, "MEDIUM", effective=22))
    w.set(unassessed("heap.top_k"))
    gaps = {g.skill_key: g for g in w.gaps().gaps}
    health = {
        k: skill_health(gaps[k], w.states[k]) for k in ("graph.traversal", "heap.top_k", "arrays.traversal")
    }
    assert health["heap.top_k"] == "unknown" and health["arrays.traversal"] == "strong"
    assert health["graph.traversal"] in ("critical", "developing")


def test_a_near_target_date_parks_what_is_not_worth_the_remaining_time() -> None:
    far = background(target_date=F0 + timedelta(weeks=38))
    near = background(
        target_date=F0 + timedelta(weeks=3)
    )  # SHARPEN phase: low-importance weak skills are parked
    for world in (far, near):
        for key in graph().skills:
            if graph().skills[key].tier == "T3":
                world.set(given(key, 1, 20, "MEDIUM", effective=12))
    assert roadmap(near).counts[PARKED] > roadmap(far).counts[PARKED]


def test_the_focus_list_is_bounded_and_follows_the_engine_rank() -> None:
    w = background()
    for key in list(graph().skills)[:12]:
        w.set(given(key, 1, 20, "MEDIUM", effective=12))
    r = roadmap(w)
    assert len(r.focus_now) <= FOCUS_SIZE
    ranks = [i.rank for i in r.focus_now]
    assert ranks == sorted(ranks)


def test_changes_list_who_entered_and_who_left_the_focus() -> None:
    before = background()
    before.set(given("graph.traversal", 3, 40, "MEDIUM", effective=33))
    after = background(as_of=F0 + timedelta(days=1))
    after.set(given("sd.caching", 2, 25, "MEDIUM", effective=18))
    changes = roadmap_changes(roadmap(before), roadmap(after))
    assert changes.changed
    assert [c.skill_key for c in changes.entered] == ["sd.caching"]
    assert [c.skill_key for c in changes.left] == ["graph.traversal"]
    assert changes.entered[0].priority_after and changes.entered[0].reason_codes
    assert roadmap_changes(roadmap(before), roadmap(before)).changed is False


def test_the_first_roadmap_is_not_reported_as_a_change() -> None:
    empty = background(as_of=F0)  # nothing in focus yesterday
    after = background(as_of=F0 + timedelta(days=1))
    after.set(given("sd.caching", 2, 25, "MEDIUM", effective=18))
    changes = roadmap_changes(roadmap(empty), roadmap(after))
    assert roadmap(after).focus_now and changes.changed is False and not changes.entered and not changes.left


def test_same_inputs_give_the_same_roadmap() -> None:
    def world():  # type: ignore[no-untyped-def]
        w = background()
        w.set(given("graph.traversal", 3, 51, "MEDIUM", effective=44))
        w.set(unassessed("heap.top_k"))
        return w

    assert roadmap(world()) == roadmap(world())
    assert roadmap(world()).items == roadmap(world()).items


def test_dates_are_plain_local_dates() -> None:
    assert isinstance(F0, date)
