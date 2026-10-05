"""Revision expectations of SCENARIOS.md (REVISION_ENGINE §3-§9), pure, real seed graph."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.domain.revision.engine import (
    backlog_minutes,
    project_revision_items,
    revision_cap,
    revision_facts,
    revision_health,
    triage_backlog,
)
from app.domain.revision.model import (
    ProblemFact,
    RevisionAction,
    RevisionItem,
    RevisionObservation,
    RowFact,
)
from app.domain.rulesets import v1
from tests.golden.harness import F0, catalog, graph, skills_where

_ids = iter(range(1, 10_000))


def attempt_obs(
    problem: int | str,
    age: int,
    outcome: str,
    points: int,
    *,
    skill: str,
    canonical: bool = False,
    difficulty: str = "MEDIUM",
    ratio: int | None = None,
    hints: int = 0,
    review: str | None = None,
    time_seconds: int | None = None,
) -> RevisionObservation:
    day = F0 - timedelta(days=age)
    pid = problem if isinstance(problem, int) else 900_000 + int(str(problem)[1:])
    return RevisionObservation(
        source_type="ATTEMPT",
        source_id=next(_ids),
        observed_on=day,
        observed_at=datetime(day.year, day.month, day.day, 6, tzinfo=UTC),
        rows=(RowFact(skill, 3, points, True, ratio),),
        revision_item_key=review,
        problem=ProblemFact(pid, difficulty, canonical, True, skill),
        outcome=outcome,
        hints_used=hints,
        time_seconds=time_seconds,
    )


def assessment_obs(
    skill: str, age: int, points: int, *, level: int = 3, review: str | None = None
) -> RevisionObservation:
    day = F0 - timedelta(days=age)
    return RevisionObservation(
        source_type="ASSESSMENT",
        source_id=next(_ids),
        observed_on=day,
        observed_at=datetime(day.year, day.month, day.day, 7, tzinfo=UTC),
        rows=(RowFact(skill, level, points, True),),
        revision_item_key=review,
        kind="CONCEPT_EXPLAIN",
    )


def project(observations: list[RevisionObservation], actions=(), extra=()):  # type: ignore[no-untyped-def]
    return project_revision_items(
        observations=observations,
        actions=list(actions),
        graph=graph(),
        as_of_date=F0,
        ruleset=v1,
        extra_items=list(extra),
    )


def item(key: str, skill: str, item_type: str, minutes: int, due: date, **kw: object) -> RevisionItem:
    values: dict[str, object] = dict(
        item_key=key,
        item_type=item_type,
        skill=skill,
        subject_ref=skill,
        ladder="STANDARD",
        state="ACTIVE",
        suspend_reason=None,
        interval_index=1,
        due_date=due,
        lapses=0,
        needs_reinforcement=False,
        created_on=date(2026, 9, 1),
        last_reviewed_on=None,
        minutes=minutes,
    )
    values.update(kw)
    return RevisionItem(**values)  # type: ignore[arg-type]


def test_s03_failed_attempts_create_reinforced_problem_items() -> None:
    obs = [
        attempt_obs("F104", 4, "PASS", 100, skill="graph.traversal"),
        attempt_obs("F105", 10, "PASS", 100, skill="graph.traversal"),
        attempt_obs("F103", 1, "FAIL", 0, skill="graph.traversal"),
        attempt_obs("F102", 3, "FAIL", 0, skill="graph.traversal"),
        attempt_obs("F101", 6, "FAIL", 0, skill="graph.traversal"),
    ]
    bg_pattern = item("PATTERN:graph.traversal", "graph.traversal", "PATTERN", 10, F0 + timedelta(days=9))
    items = project(obs, extra=[bg_pattern]).items  # BG history: the pattern item already exists
    problem_items = {k: v for k, v in items.items() if k.startswith("PROBLEM:")}
    assert sorted(problem_items) == ["PROBLEM:900101", "PROBLEM:900102", "PROBLEM:900103"]
    due = {
        k: (v.due_date, v.interval_index, v.needs_reinforcement, v.total_minutes(10))
        for k, v in problem_items.items()
    }
    assert due == {
        "PROBLEM:900103": (date(2026, 11, 2), 0, True, 35),
        "PROBLEM:900102": (date(2026, 10, 31), 0, True, 35),
        "PROBLEM:900101": (date(2026, 10, 28), 0, True, 35),
    }
    assert items["PATTERN:graph.traversal"] == bg_pattern  # unlinked practice does not move the schedule
    fresh = project(obs).items["PATTERN:graph.traversal"]  # without history the first scoring row creates it
    assert (fresh.interval_index, fresh.due_date) == (1, date(2026, 10, 26))


def test_s05_third_lapse_suspends_as_leech_and_strong_row_reactivates() -> None:
    start = item(
        "CS:db.isolation_mvcc",
        "db.isolation_mvcc",
        "CS",
        10,
        date(2026, 11, 1),
        interval_index=0,
        lapses=2,
        needs_reinforcement=True,
    )
    review = assessment_obs("db.isolation_mvcc", 1, 40, review="CS:db.isolation_mvcc")
    projection = project([review], extra=[start])
    leech = projection.items["CS:db.isolation_mvcc"]
    assert (leech.state, leech.suspend_reason, leech.lapses) == ("SUSPENDED", "LEECH", 3)
    assert projection.reviews[-1].outcome == "FAIL"
    assert revision_facts(projection, F0)["db.isolation_mvcc"] == (0, False, True)
    later = assessment_obs("db.isolation_mvcc", 0, 75, level=3)
    revived = project([review, later], extra=[start]).items["CS:db.isolation_mvcc"]
    assert (revived.state, revived.interval_index, revived.lapses, revived.due_date) == (
        "ACTIVE",
        0,
        1,
        date(2026, 11, 3),
    )


def test_s06_fails_and_partial_create_problem_items() -> None:
    obs = [
        attempt_obs("F201", 20, "PASS", 100, skill="sliding_window.core"),
        attempt_obs("F202", 25, "PASS", 100, skill="sliding_window.core"),
        attempt_obs("F203", 2, "FAIL", 0, skill="sliding_window.core"),
        attempt_obs("F204", 5, "FAIL", 0, skill="sliding_window.core"),
        attempt_obs("F205", 9, "FAIL", 0, skill="sliding_window.core"),
        attempt_obs("F206", 12, "PARTIAL", 50, skill="sliding_window.core"),
    ]
    bg_pattern = item(
        "PATTERN:sliding_window.core", "sliding_window.core", "PATTERN", 10, F0 + timedelta(days=5)
    )
    items = project(obs, extra=[bg_pattern]).items
    got = {k: (v.interval_index, v.due_date) for k, v in items.items() if k.startswith("PROBLEM:")}
    assert got == {
        "PROBLEM:900203": (0, date(2026, 11, 1)),
        "PROBLEM:900204": (0, date(2026, 10, 29)),
        "PROBLEM:900205": (0, date(2026, 10, 25)),
        "PROBLEM:900206": (1, date(2026, 10, 24)),
    }
    assert items["PROBLEM:900206"].days_overdue(F0) == 9
    health = revision_health(project(obs, extra=[bg_pattern]), graph(), set(), F0, v1)
    assert health.overdue_items == ("PROBLEM:900205", "PROBLEM:900206")  # 8 and 9 days > 7


def test_s08_slow_clean_passes_create_index_1_items() -> None:
    obs = [
        attempt_obs(f"F30{i}", age, "PASS", 100, skill="binary_search.basic", ratio=ratio)
        for i, (age, ratio) in enumerate([(3, 16000), (7, 13666), (11, 17333)], 1)
    ]
    got = sorted(
        (v.interval_index, v.due_date, v.minutes)
        for k, v in project(obs).items.items()
        if k.startswith("PROBLEM:")
    )
    assert got == [(1, date(2026, 10, 25), 25), (1, date(2026, 10, 29), 25), (1, date(2026, 11, 2), 25)]


def test_clean_fast_noncanonical_pass_creates_no_problem_item_but_canonical_does() -> None:
    fast = attempt_obs("F401", 2, "PASS", 100, skill="heap.top_k", ratio=8000)
    assert not [k for k in project([fast]).items if k.startswith("PROBLEM:")]
    canonical = attempt_obs(17, 2, "PASS", 100, skill="heap.top_k", canonical=True, ratio=8000)
    created = project([canonical]).items["PROBLEM:17"]
    assert (created.interval_index, created.due_date) == (2, date(2026, 11, 7))


def seed_problem_item(pid: int, due: date) -> RevisionItem:
    problem = next(p for p in catalog().problems if p.id == pid)
    primary = next(ps.skill for ps in problem.skills if ps.mapping_weight_bp == 10000)
    minutes = int(v1.REVISION_ITEM_MINUTES[f"PROBLEM_{problem.difficulty}"])
    return item(f"PROBLEM:{pid}", primary, "PROBLEM", minutes, due, subject_ref=str(pid))


def s11_items() -> list[RevisionItem]:
    out = [seed_problem_item(pid, date(2026, 10, 8)) for pid in (15, 20, 27, 3, 4, 6)]
    out += [seed_problem_item(pid, date(2026, 10, 10)) for pid in (9, 12, 16, 22)]
    for n, key in enumerate(skills_where(component="cs", tier="T2")):
        out.append(item(f"CS:{key}", key, "CS", 10, date(2026, 10, 20) + timedelta(days=n // 2)))
    for key in (
        "python.core_syntax",
        "python.collections",
        "lld.design_patterns",
        "lld.extensibility",
        "engineering.debugging",
    ):
        out.append(item(f"CONCEPT:{key}", key, "CONCEPT", 10, date(2026, 10, 22)))
    for key in skills_where(component="system_design", tier="T3"):
        out.append(item(f"SD:{key}", key, "SD", 20, date(2026, 10, 18)))
    for key in skills_where(component="cs", tier="T3"):
        out.append(item(f"CS:{key}", key, "CS", 10, date(2026, 10, 19)))
    return out


def test_s11_fixture_matches_the_scenario_table() -> None:
    tiers = {i.item_key: graph().skills[i.skill].tier for i in s11_items()}
    assert [tiers[f"PROBLEM:{p}"] for p in (15, 20, 27, 3, 4, 6)] == ["T1"] * 6
    assert [tiers[f"PROBLEM:{p}"] for p in (9, 12, 16, 22)] == ["T2"] * 4
    assert [i.minutes for i in s11_items()[:2]] == [15, 15]  # EASY problems #15, #20


def test_s11_backlog_triage() -> None:
    items = {i.item_key: i for i in s11_items()}
    assert (
        len(skills_where(component="cs", tier="T2")) == 10
        and len(skills_where(component="cs", tier="T3")) == 7
    )
    assert revision_cap(90, v1) == 36
    assert backlog_minutes(items, set(), F0, v1) == 540  # D-065: #22 is EASY in the seed
    actions = triage_backlog(
        items=items, graph=graph(), parked=set(), daily_budget=90, as_of_date=F0, ruleset=v1
    )
    assert len(actions) == 24 and {a.action for a in actions} == {"SUSPEND"}  # D-065
    suspended = [a.item_key for a in actions]
    t3_cs = sorted(f"CS:{k}" for k in skills_where(component="cs", tier="T3"))
    assert suspended[:7] == t3_cs  # due 10-19, importance 50, key asc
    assert suspended[7:12] == sorted(f"SD:{k}" for k in skills_where(component="system_design", tier="T3"))
    concept_block = suspended[16:21]
    assert all(k.startswith("CONCEPT:") for k in concept_block)  # due 10-22: CONCEPT < CS by key
    record = [
        RevisionAction(n, key, "SUSPEND", "BACKLOG_TRIAGE", F0, datetime(2026, 11, 2, 4, tzinfo=UTC))
        for n, key in enumerate(suspended, 1)
    ]
    after = project([], record, s11_items()).items
    assert backlog_minutes(after, set(), F0, v1) == 250
    remaining = sorted(k for k, v in after.items() if v.state == "ACTIVE")
    assert (
        len([k for k in remaining if k.startswith("PROBLEM:")]) == 10
        and len([k for k in remaining if k.startswith("CS:")]) == 3
    )
    assert all(graph().skills[after[k].skill].tier != "T1" for k in suspended)
    health = revision_health(project([], record, s11_items()), graph(), set(), F0, v1)
    assert health.overdue_t1_t2_over_7d == 13  # 6 + 4 + 3 (D-065); suspended items not counted


def test_auto_resume_below_three_caps_restores_most_important_first() -> None:
    items = {
        i.item_key: i
        for i in [
            item(
                "CS:a",
                "db.indexing",
                "CS",
                10,
                date(2026, 10, 1),
                state="SUSPENDED",
                suspend_reason="BACKLOG_TRIAGE",
                due_before_suspension=date(2026, 10, 1),
            ),
            item(
                "CS:b",
                "db.nosql_tradeoffs",
                "CS",
                10,
                date(2026, 10, 1),
                state="SUSPENDED",
                suspend_reason="BACKLOG_TRIAGE",
                due_before_suspension=date(2026, 9, 1),
            ),
            item(
                "CS:c",
                "os.memory_virtual",
                "CS",
                10,
                date(2026, 10, 1),
                state="SUSPENDED",
                suspend_reason="MANUAL",
            ),
        ]
    }
    actions = triage_backlog(
        items=items, graph=graph(), parked=set(), daily_budget=90, as_of_date=F0, ruleset=v1
    )
    assert [(a.item_key, a.action) for a in actions] == [
        ("CS:a", "RESUME"),
        ("CS:b", "RESUME"),
    ]  # manual stays


def test_s16_parked_skill_items_are_not_backlog_or_g7() -> None:
    overdue = item(
        "SD:sd.distributed_coordination", "sd.distributed_coordination", "SD", 20, date(2026, 10, 23)
    )
    items = {overdue.item_key: overdue}
    parked = {"sd.distributed_coordination"}
    assert backlog_minutes(items, parked, F0, v1) == 0
    projection = project([], (), [overdue])
    assert revision_health(projection, graph(), parked, F0, v1).overdue_t1_t2_over_7d == 0
    assert projection.items[overdue.item_key].state == "ACTIVE"  # unchanged, only not scheduled


def test_s04_graduated_t2_item_has_a_maintenance_check() -> None:
    graduated = item(
        "PATTERN:binary_search.boundaries",
        "binary_search.boundaries",
        "PATTERN",
        10,
        date(2026, 10, 18),
        state="GRADUATED",
        interval_index=5,
    )
    projection = project([], (), [graduated])
    assert projection.items[graduated.item_key].is_due(F0)
    assert backlog_minutes(projection.items, set(), F0, v1) == 0  # maintenance never counts toward backlog


def test_s20_two_items_due_today() -> None:
    due = [
        item("CS:db.indexing", "db.indexing", "CS", 10, F0),
        item("PATTERN:heap.top_k", "heap.top_k", "PATTERN", 10, F0),
    ]
    projection = project([], (), due)
    assert backlog_minutes(projection.items, set(), F0, v1) == 20
    assert revision_health(projection, graph(), set(), F0, v1).overdue_t1_t2_over_7d == 0
