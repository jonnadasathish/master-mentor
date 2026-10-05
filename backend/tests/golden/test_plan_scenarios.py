"""Daily plans and mentor messages of SCENARIOS.md S01-S20 (MENTOR_ENGINE §3-§9), pure, real seed catalog.

Readiness is given here as the scenario's expected readiness (the mentor consumes it); Slice 8 computes it.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.mentor.model import Blocker, MockRoundInfo, ProblemInfo, ReadinessView
from tests.golden.harness import (
    F0,
    background,
    cold_start,
    declared_unknown,
    given,
    plan,
    skills_where,
    summary,
)
from tests.golden.test_gap_scenarios import mock_world, s03_world
from tests.golden.test_revision_scenarios import item, s11_items
from tests.scenario_support import row

G9 = Blocker("G9", "0 of 3 final simulations")
DEVELOPING = ReadinessView("DEVELOPING", (G9,), simulation_eligible=True, weighted_score=75)
M_OK = [
    MockRoundInfo(10, "DSA", date(2026, 10, 28)),
    MockRoundInfo(9, "CS", date(2026, 10, 26)),
    MockRoundInfo(8, "PROJECT_DEEP_DIVE", date(2026, 10, 25)),
    MockRoundInfo(7, "BEHAVIORAL", date(2026, 10, 24)),
    MockRoundInfo(6, "LLD", date(2026, 10, 22)),
    MockRoundInfo(5, "SYSTEM_DESIGN", date(2026, 10, 20)),
]


def fixture_problem(code: str, skill: str, attempts: int = 1, last_age: int = 1) -> ProblemInfo:
    pid = 900_000 + int(code[1:])
    return ProblemInfo(
        pid, code.lower(), "MEDIUM", False, ((skill, 10000),), attempts, F0 - timedelta(days=last_age)
    )


def problem_item(code: str, skill: str, due: date, index: int, minutes: int = 25):  # type: ignore[no-untyped-def]
    return item(
        f"PROBLEM:{code}",
        skill,
        "PROBLEM",
        minutes,
        due,
        interval_index=index,
        needs_reinforcement=index == 0,
        subject_ref=str(900_000 + int(code[1:])),
    )


def test_s01_cold_start_battery_plan() -> None:
    w = cold_start(readiness=ReadinessView())
    w.battery_done = set()
    p = plan(w)
    assert summary(p) == [("BASE:M0-B01", None, "DIAGNOSE", 15), ("BASE:M0-B02", None, "DIAGNOSE", 60)]
    assert p.items[1].problem_ids == (4, 2)  # greedy cover: 3sum, then group-anagrams
    assert (p.allocated_minutes, p.unallocated_minutes, p.calibration_mode) == (75, 15, True)
    assert (p.message.rule, p.message.text) == (
        "CALIBRATION",
        "Calibration: 0/123 required skills measured. Today's diagnostics: M0-B01, M0-B02. No new material until "
        "the baseline is complete.",
    )


def test_s02_weak_system_design() -> None:
    w = background(
        readiness=ReadinessView("FOUNDATION", (Blocker("G1", "System Design 43 < 45", "system_design"),))
    )
    for key in skills_where(component="system_design"):
        w.set(given(key, 3, 50, "MEDIUM"))
    w.track_minutes = {**dict(w.track_minutes or {}), **{"system_design": 30}}
    from tests.golden.harness import profile

    w.track_minutes = {**profile().track_minutes, "system_design": 30}
    p = plan(w)
    assert summary(p) == [
        ("GAP:sd.caching", "system_design.timed", "TIMED", 50),
        ("GAP:sd.data_modeling", "system_design.drill", "TIMED", 20),
    ]
    assert p.items[0].score == 60 and "TRACK_FLOOR" in p.items[0].reason_codes
    assert {d.key: d.reason for d in p.dropped}["GAP:sd.database_scaling"] == "FOCUS_LIMIT"
    assert p.message.text == "FOUNDATION: System Design 43 < 45. Today's work targets it: sd.caching."


def test_s03_new_topic_held_pattern_drill() -> None:
    w = s03_world()
    w.readiness = ReadinessView(
        "FOUNDATION", (Blocker("G1", "dp.fundamentals level L0 < L3", skill="dp.fundamentals"),)
    )
    w.extra_problems = [
        fixture_problem(f"F10{i}", "graph.traversal", last_age=a) for i, a in enumerate((6, 3, 1, 4, 10), 1)
    ]
    for code, age in (("F103", 1), ("F102", 3), ("F101", 6)):
        w.revision_items[f"PROBLEM:{code}"] = problem_item(
            code, "graph.traversal", F0 - timedelta(days=age) + timedelta(days=1), 0
        )
    p = plan(w)
    assert summary(p) == [
        ("REV:PROBLEM:F101", "revision.reinforce", "REINFORCE", 35),
        ("GAP:graph.traversal", "dsa.pattern_drill", "PATTERN_DRILL", 25),
    ]
    assert [i.score for i in p.items] == [85, 57]
    assert p.items[1].problem_ids[:2] == (28, 29) and len(p.items[1].problem_ids) == 5
    dropped = {d.key: d.reason for d in p.dropped}
    assert dropped["REV:PROBLEM:F102"] == dropped["REV:PROBLEM:F103"] == "PER_SKILL_LIMIT"
    assert dropped["GAP:dp.fundamentals"] == "NEW_TOPIC_HOLD"
    assert p.message.text == (
        "Do not start dp.fundamentals today. graph.traversal PATTERN_RECOGNITION is HIGH (57): 3 of your last 4 "
        "unseen graph.traversal problems used the wrong approach."
    )


def test_s04_retention_reinforce_and_maintenance_check() -> None:
    w = background(readiness=DEVELOPING)
    w.evidence(
        "binary_search.boundaries", [row(4, 100, 130, "a"), row(4, 100, 135, "b"), row(3, 100, 140, "c")]
    )
    w.revision_items["PATTERN:binary_search.boundaries"] = item(
        "PATTERN:binary_search.boundaries",
        "binary_search.boundaries",
        "PATTERN",
        10,
        date(2026, 10, 18),
        state="GRADUATED",
        interval_index=5,
    )
    p = plan(w)
    assert summary(p) == [
        ("GAP:binary_search.boundaries", "dsa.reinforce", "REINFORCE", 30),
        ("REV:PATTERN:binary_search.boundaries", "revision.pattern", "REVISION", 10),
    ]
    assert p.items[0].problem_ids == (16,) and p.items[1].score == 45
    assert p.message.text == (
        "Top priority: binary_search.boundaries (HIGH, 56): RETENTION. Peak 72, now 30; last practiced 130 days ago."
    )


def test_s05_leech_relearn() -> None:
    w = background(readiness=DEVELOPING)
    w.evidence(
        "db.isolation_mvcc",
        [
            row(3, 80, 41, "pa"),
            row(3, 75, 36, "pb"),
            row(3, 45, 16, "pc"),
            row(3, 30, 9, "pc"),
            row(3, 40, 1, "pc"),
        ],
    )
    w.revision_items["CS:db.isolation_mvcc"] = item(
        "CS:db.isolation_mvcc",
        "db.isolation_mvcc",
        "CS",
        10,
        date(2026, 11, 2),
        state="SUSPENDED",
        suspend_reason="LEECH",
        interval_index=0,
        lapses=3,
        needs_reinforcement=True,
    )
    from app.domain.gaps.model import RevisionFacts

    w.revision["db.isolation_mvcc"] = RevisionFacts(has_leech=True)
    p = plan(w)
    assert summary(p) == [
        ("GAP:db.isolation_mvcc", "cs.guided", "GUIDED", 20),
        ("FOLLOW:db.isolation_mvcc", "cs.independent", "INDEPENDENT", 20),
    ]
    assert p.message.text == (
        "You failed the db.isolation_mvcc revision 3 times. Stop re-reading; re-learn it with guided practice today."
    )


def test_s06_overconfident_closed_book_check() -> None:
    w = background(readiness=DEVELOPING)
    w.evidence(
        "sliding_window.core",
        [
            row(3, 100, 20, "F201", self_rating_before=3, pattern_identified=True),
            row(3, 100, 25, "F202", self_rating_before=3, pattern_identified=True),
            row(3, 0, 2, "F203", self_rating_before=5, pattern_identified=True),
            row(3, 0, 5, "F204", self_rating_before=4, pattern_identified=True),
            row(3, 0, 9, "F205", self_rating_before=5, pattern_identified=True),
            row(3, 50, 12, "F206", self_rating_before=4, pattern_identified=True),
        ],
    )
    for code, due, index in (
        ("F203", date(2026, 11, 1), 0),
        ("F204", date(2026, 10, 29), 0),
        ("F205", date(2026, 10, 25), 0),
        ("F206", date(2026, 10, 24), 1),
    ):
        w.revision_items[f"PROBLEM:{code}"] = problem_item(code, "sliding_window.core", due, index)
    w.extra_problems = [fixture_problem(f"F20{i}", "sliding_window.core") for i in range(1, 7)]
    p = plan(w)
    assert summary(p) == [
        ("REV:PROBLEM:F206", "revision.problem", "REVISION", 25),
        ("GAP:sliding_window.core", "dsa.independent", "INDEPENDENT", 35),
    ]
    assert p.items[0].score == 89
    assert p.message.text == (
        "You rated yourself ≥ 4 before 3 attempts on sliding_window.core that you failed. Today is a closed-book check."
    )


def test_s07_underconfident() -> None:
    w = background(readiness=DEVELOPING)
    w.evidence(
        "heap.top_k",
        [
            row(
                4,
                100,
                a,
                f"h{a}",
                self_rating_before=r,
                depth_points=60,
                timed=True,
                within_limit=True,
                time_ratio_bp=8000,
            )
            for a, r in ((3, 2), (6, 1), (10, 2))
        ],
    )
    p = plan(w)
    assert summary(p) == [
        ("GAP:heap.top_k", "dsa.explain", "EXPLAIN", 40),
        ("FOLLOW:heap.top_k", "dsa.transfer", "TRANSFER", 50),
    ]
    assert p.message.text == (
        "Your evidence on heap.top_k (L4, score 72) is stronger than your self-ratings (2, 1, 2). Trust it and push "
        "to EXPLAIN."
    )


def test_s08_switch_to_timed() -> None:
    w = background(readiness=DEVELOPING)
    w.evidence(
        "binary_search.basic",
        [
            row(3, 100, 3, "a", time_ratio_bp=16000),
            row(3, 100, 7, "b", time_ratio_bp=13666),
            row(3, 100, 11, "c", time_ratio_bp=17333),
        ],
    )
    for code, due in (
        ("F301", date(2026, 11, 2)),
        ("F302", date(2026, 10, 29)),
        ("F303", date(2026, 10, 25)),
    ):
        w.revision_items[f"PROBLEM:{code}"] = problem_item(code, "binary_search.basic", due, 1)
    p = plan(w)
    assert summary(p) == [
        ("REV:PROBLEM:F303", "revision.problem", "REVISION", 25),
        ("GAP:binary_search.basic", "dsa.timed", "TIMED", 40),
    ]
    assert [i.score for i in p.items][0] == 88
    assert p.message.text == (
        "You solve binary_search.basic independently (L3), but median time is 160% of target. Switch from learning "
        "to timed practice."
    )


def test_s09_communication_gap() -> None:
    w = background(
        readiness=ReadinessView("DEVELOPING", (Blocker("G2", "Coding & Execution 67 < 70", "coding"), G9))
    )
    w.evidence(
        "trees.traversal",
        [
            row(4, 100, a, f"t{a}", communication_points=c, depth_points=60)
            for a, c in ((2, 40), (5, 50), (8, 50))
        ],
    )
    w.evidence(
        "execution.think_aloud",
        [
            row(4, x, a, f"t{a}", rule="DERIVED", communication_points=x)
            for a, x in ((2, 40), (5, 50), (8, 50))
        ],
    )
    p = plan(w)
    assert summary(p) == [
        ("GAP:execution.think_aloud", "coding.think_aloud", "THINK_ALOUD", 40),
        ("GAP:trees.traversal", "generic.think_aloud", "THINK_ALOUD", 30),
    ]
    assert (
        p.message.text
        == "Your solutions are correct, but your explanation scores average 47/100. Practice out loud, recorded."
    )


def test_s10_prerequisite_unlock() -> None:
    w = background(
        readiness=ReadinessView(
            "FOUNDATION", (Blocker("G1", "dp.fundamentals level L1 < L3", skill="dp.fundamentals"),)
        )
    )
    w.set(given("dp.fundamentals", 1, 25, "MEDIUM"))
    w.set(given("recursion.fundamentals", 3, 50, "MEDIUM"))
    p = plan(w)
    assert summary(p) == [
        ("GAP:recursion.fundamentals", "dsa.timed", "TIMED", 40),
        ("FOLLOW:recursion.fundamentals", "dsa.explain", "EXPLAIN", 40),
    ]
    assert (
        p.message.text
        == "Do not start dp.fundamentals yet. recursion.fundamentals (50/60) blocks it, so fix it first."
    )


def test_s11_backlog_plan_after_triage() -> None:
    from app.domain.revision.engine import triage_backlog
    from app.domain.rulesets import v1
    from tests.golden.harness import graph

    items = {i.item_key: i for i in s11_items()}
    actions = triage_backlog(
        items=items, graph=graph(), parked=set(), daily_budget=90, as_of_date=F0, ruleset=v1
    )
    from dataclasses import replace as dc_replace

    for a in actions:
        items[a.item_key] = dc_replace(items[a.item_key], state="SUSPENDED", suspend_reason="BACKLOG_TRIAGE")
    w = background(readiness=DEVELOPING)
    w.revision_items = items
    w.triage_suspended = tuple(a.item_key for a in actions)
    p = plan(w)
    keys = [i.candidate_key for i in p.items]
    cs_due_1020 = sorted(
        k for k, v in items.items() if k.startswith("CS:") and v.due_date == date(2026, 10, 20)
    )
    assert keys == [
        "REV:PROBLEM:15",
        "REV:PROBLEM:20",
        "REV:PROBLEM:27",
        "REV:PROBLEM:3",
        f"REV:{cs_due_1020[0]}",
    ]
    assert p.allocated_minutes == 90 and p.items[-1].score == 88
    dropped = {d.key: d.reason for d in p.dropped}
    assert dropped["REV:PROBLEM:4"] == dropped["REV:PROBLEM:6"] == "BUDGET"
    assert p.message.text == (
        "Revision backlog is 250 min, more than a day's budget. Revisions are limited to 36 min/day when other work "
        "exists; 24 low-importance items were suspended."
    )


def test_s12_deadline_infeasible() -> None:
    w = background(
        target_date=date(2027, 1, 11),
        readiness=ReadinessView("FOUNDATION", (Blocker("G1", "LLD / OOD 20 < 45", "lld"),)),
    )
    for key in skills_where(component="lld"):
        w.set(given(key, 2, 35, "LOW"))
    p = plan(w)
    assert summary(p) == [("GAP:lld.requirements_entities", "lld.independent", "INDEPENDENT", 60)]
    assert p.message.text == (
        "At the current pace LLD / OOD cannot reach target by 2027-01-11 (needs 900 min, 750 available). Only "
        "critical skills are scheduled there; consider moving the date."
    )


def test_s13_one_new_topic_per_day() -> None:
    w = background(readiness=DEVELOPING)
    w.set(declared_unknown("trie.core"))
    w.set(declared_unknown("os.memory_virtual"))
    p = plan(w)
    assert summary(p) == [
        ("GAP:os.memory_virtual", "cs.learn", "LEARN", 40),
        ("FOLLOW:os.memory_virtual", "cs.guided", "GUIDED", 20),
    ]
    assert {d.key: d.reason for d in p.dropped}["GAP:trie.core"] == "NEW_TOPIC_LIMIT"
    assert (
        p.message.text
        == "Top priority: os.memory_virtual (MEDIUM, 33): KNOWLEDGE. Declared unknown, new topic in milestone CS-2."
    )


def consolidate_mocks(last: date, oldest_type: str, oldest: date) -> list[MockRoundInfo]:
    others = [
        t
        for t in ("DSA", "CS", "LLD", "SYSTEM_DESIGN", "BEHAVIORAL", "PROJECT_DEEP_DIVE")
        if t != oldest_type
    ]
    rounds = [MockRoundInfo(100, others[0], last)]
    rounds += [MockRoundInfo(90 + n, t, last - timedelta(days=n + 1)) for n, t in enumerate(others[1:])]
    rounds.append(MockRoundInfo(80, oldest_type, oldest))
    return rounds


def test_s14_consolidate_mock_and_stop_studying() -> None:
    w = background(target_date=date(2027, 1, 11), readiness=DEVELOPING)
    w.evidence("trie.core", [row(0, 0, 3, "study", is_scoring=False, kind="STUDY_SESSION", study_minutes=45)])
    w.set(declared_unknown("trie.core"), w.facts["trie.core"])
    w.set(given("sd.storage_search", 2, 45, "LOW", effective=30))
    w.study_minutes_7d = {"trie.core": 45}
    w.mock_rounds = consolidate_mocks(date(2026, 10, 25), "SYSTEM_DESIGN", date(2026, 10, 20))
    p = plan(w)
    assert summary(p) == [("MOCK:SYSTEM_DESIGN", "mock.round", "SIMULATE", 60)]
    assert (
        p.items[0].score == 55 and {d.key: d.reason for d in p.dropped}["GAP:sd.storage_search"] == "BUDGET"
    )
    assert len(p.stop_list) == 11
    assert (
        p.message.text
        == "Stop trie.core: parked until after 2027-01-11 (CONSOLIDATE). Move that time to sd.storage_search."
    )


def test_s15_sharpen() -> None:
    w = background(target_date=date(2026, 11, 23), readiness=DEVELOPING)
    w.set(given("heap.two_heaps_merge_k", 2, 40, "LOW", effective=25))
    w.set(given("graph.shortest_path", 1, 25, "LOW", effective=10))
    w.set(given("execution.time_management", 4, 66, "MEDIUM"))
    w.mock_rounds = consolidate_mocks(date(2026, 10, 29), "BEHAVIORAL", date(2026, 10, 15))
    p = plan(w)
    assert summary(p) == [
        ("MOCK:BEHAVIORAL", "mock.round", "SIMULATE", 45),
        ("GAP:execution.time_management", "coding.execution_drill", "EXPLAIN", 40),
    ]
    assert not any(i.stage == "LEARN" for i in p.items)
    assert (
        p.message.text
        == "3 weeks left. No new topics. Sharpen execution.time_management and keep mocks going."
    )


def test_s16_parked_topic_stays_quiet() -> None:
    w = background(target_date=date(2027, 1, 11), readiness=DEVELOPING)
    w.set(given("db.nosql_tradeoffs", 1, 20, "LOW"))
    w.study_minutes_7d = {"db.nosql_tradeoffs": 60}
    w.revision_items["SD:sd.distributed_coordination"] = item(
        "SD:sd.distributed_coordination", "sd.distributed_coordination", "SD", 20, date(2026, 10, 23)
    )
    w.mock_rounds = consolidate_mocks(date(2026, 10, 24), "CS", date(2026, 10, 14))
    p = plan(w)
    assert summary(p) == [("MOCK:CS", "mock.round", "SIMULATE", 45)]
    assert (
        p.message.text
        == "Stop db.nosql_tradeoffs: parked until after 2027-01-11 (CONSOLIDATE). Move that time to today's plan."
    )


def test_s17_mock_gap() -> None:
    prior = [
        row(5, 100, 10, "a"),
        row(5, 100, 20, "b"),
        row(4, 100, 30, "c"),
        row(4, 100, 40, "d"),
        row(3, 100, 50, "e"),
        row(4, 60, 25, "f"),
    ]
    w = mock_world("sd.capacity_estimation", prior, 40)
    caching = [row(5, 100, a, f"c{a}") for a in (8, 16, 24)] + [
        row(4, 100, 32, "d"),
        row(4, 100, 40, "e"),
        row(3, 100, 50, "f"),
    ]
    w.evidence(
        "sd.caching", [*caching, row(7, 55, 1, "mock_round:100", is_weakness=True)], mock_weakness=True
    )
    w.readiness = ReadinessView(
        "DEVELOPING", (Blocker("G4", "sd.caching effective 55 < 65", skill="sd.caching"), G9)
    )
    w.mock_rounds = [*M_OK, MockRoundInfo(100, "SYSTEM_DESIGN", date(2026, 11, 1))]
    p = plan(w)
    assert summary(p) == [("GAP:sd.capacity_estimation", "system_design.simulate", "SIMULATE", 50)]
    assert (
        p.message.text
        == "sd.capacity_estimation: practice level L5, but your last mock scored 40. Practice under interview conditions."
    )


def test_s18_behavioral_blocker() -> None:
    from tests.golden.harness import profile

    keys = ["behavioral.ownership", "behavioral.impact", "communication.structured_answers"]
    w = background(
        readiness=ReadinessView(
            "FOUNDATION", tuple(Blocker("G1", f"{k} level L2 < L3", skill=k) for k in sorted(keys))
        )
    )
    for key in keys:
        w.set(given(key, 2, 40, "MEDIUM"))
    w.track_minutes = {**profile().track_minutes, "behavioral_project": 10}
    p = plan(w)
    assert summary(p) == [
        ("GAP:behavioral.impact", "behavioral.independent", "INDEPENDENT", 15),
        ("GAP:behavioral.ownership", "behavioral.independent", "INDEPENDENT", 15),
        ("FOLLOW:behavioral.impact", "behavioral.timed", "TIMED", 15),
    ]
    assert p.items[0].score == 73
    assert {d.key: d.reason for d in p.dropped}["GAP:communication.structured_answers"] == "FOCUS_LIMIT"
    assert (
        p.message.text
        == "FOUNDATION: behavioral.impact level L2 < L3. Today's work targets it: behavioral.impact."
    )


def test_s19_final_simulation_weakness() -> None:
    prior = [row(5, 100, a, f"d{a}") for a in (9, 19, 44)] + [
        row(4, 100, 29, "e"),
        row(4, 100, 35, "f"),
        row(3, 100, 55, "g"),
    ]
    w = mock_world("sd.deep_dive_bottlenecks", prior, 55)
    w.readiness = ReadinessView(
        "DEVELOPING",
        (Blocker("G4", "sd.deep_dive_bottlenecks effective 55 < 65", skill="sd.deep_dive_bottlenecks"), G9),
    )
    w.mock_rounds = [*M_OK, MockRoundInfo(100, "SYSTEM_DESIGN", date(2026, 11, 1))]
    p = plan(w)
    assert summary(p) == [("GAP:sd.deep_dive_bottlenecks", "system_design.simulate", "SIMULATE", 50)]
    assert p.message.text == (
        "sd.deep_dive_bottlenecks: practice level L5, but your last mock scored 55. Practice under interview conditions."
    )


def test_s20_interview_ready_maintains() -> None:
    w = background(
        readiness=ReadinessView("INTERVIEW_READY", (), simulation_eligible=True, weighted_score=75)
    )
    w.mock_rounds = list(M_OK)
    w.revision_items = {
        "CS:db.indexing": item("CS:db.indexing", "db.indexing", "CS", 10, F0),
        "PATTERN:heap.top_k": item("PATTERN:heap.top_k", "heap.top_k", "PATTERN", 10, F0),
    }
    p = plan(w)
    assert summary(p) == [
        ("REV:CS:db.indexing", "revision.cs", "REVISION", 10),
        ("REV:PATTERN:heap.top_k", "revision.pattern", "REVISION", 10),
    ]
    assert [i.score for i in p.items] == [70, 70] and p.unallocated_minutes == 70
    assert (
        p.message.text == "Interview-ready. Maintain: revisions, a mock at least every 7 days, no new topics."
    )


def test_bg_plan_is_empty_and_deterministic() -> None:
    first = plan(background(readiness=DEVELOPING))
    assert (
        first.items == ()
        and first.message.text == "No gaps above threshold today. Revisions and maintenance only."
    )
    assert plan(background(readiness=DEVELOPING)) == first
