"""GAP_ENGINE §12 worked examples and the gap expectations of SCENARIOS.md S01-S20 (pure, real seed)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.gaps.facts import MockRoundSummary, mock_weakness_skills
from app.domain.gaps.model import RevisionFacts
from app.domain.readiness.components import ComponentScore, ComponentScores
from app.domain.rulesets import v1
from tests.golden.harness import (
    background,
    cold_start,
    declared_unknown,
    gap_summary,
    given,
    graph,
    skills_where,
)
from tests.scenario_support import row

BG_COMPONENTS = {
    "dsa": 76,
    "coding": 73,
    "cs": 75,
    "lld": 77,
    "system_design": 76,
    "behavioral": 75,
    "project": 73,
}


def with_dsa(components: ComponentScores, score: int) -> ComponentScores:
    dsa = components.components["dsa"]
    patched = {**components.components, "dsa": ComponentScore("dsa", score, dsa.assessed_pct, 100, 1)}
    return ComponentScores(patched, components.weighted_score, components.limiting_component)


# ------------------------------------------------------------------------------- fixtures sanity


def test_bg_component_scores_match_f0() -> None:
    comps = background().components()
    assert {k: c.score for k, c in comps.components.items()} == BG_COMPONENTS
    assert comps.weighted_score == 75


def test_bg_has_no_actionable_gaps() -> None:  # S20 gap part
    report = background().gaps()
    assert report.phase == "BUILD" and report.weeks_left == Decimal(34)
    assert report.top_assessed() == [] and all(g.status == "NONE" for g in report.gaps)


# ------------------------------------------------------------------------------- §12 examples


def test_g2_large_gap_low_importance_vs_small_gap_high_importance() -> None:
    world = background()
    world.set(given("trie.core", 1, 35, "LOW", effective=20))
    world.set(given("heap.top_k", 4, 70, "HIGH"))
    comps = with_dsa(world.components(), 60)
    report = world.gaps(comps)
    trie, heap = report.by_skill()["trie.core"], report.by_skill()["heap.top_k"]
    assert (trie.raw_gap, trie.severity, trie.pressure_bp, trie.priority, trie.status) == (
        45,
        Decimal("22.5"),
        12000,
        27,
        "MEDIUM",
    )
    assert (heap.raw_gap, heap.pressure_bp, heap.priority, heap.status) == (10, 12000, 12, "LOW")
    world.set(given("heap.top_k", 4, 60, "HIGH"))
    alt = world.gaps(comps).by_skill()["heap.top_k"]
    assert (alt.pressure_bp, alt.priority, alt.status) == (13500, 27, "MEDIUM")


def test_g3_weak_prerequisite_vs_weak_downstream() -> None:
    world = background()
    world.set(given("dp.fundamentals", 1, 25, "MEDIUM"))
    world.set(given("recursion.fundamentals", 3, 50, "MEDIUM"))
    report = world.gaps(with_dsa(world.components(), 60))
    dp, rec = report.by_skill()["dp.fundamentals"], report.by_skill()["recursion.fundamentals"]
    assert (dp.raw_gap, dp.pressure_bp, dp.priority, dp.status) == (62, 13500, 84, "BLOCKED")
    assert [(b.skill, b.score, b.min_score) for b in dp.blocked_by] == [("recursion.fundamentals", 50, 60)]
    assert (rec.priority, rec.status) == (76, "CRITICAL") and "UNLOCKS:dp.fundamentals" in rec.reason_codes


# ------------------------------------------------------------------------------- scenarios


def test_s01_cold_start() -> None:
    report = cold_start().gaps()
    statuses = [g.status for g in report.gaps]
    assert statuses.count("UNASSESSED") == 32 and statuses.count("BLOCKED") == 129
    gaps = report.by_skill()
    for key, priority in [
        ("dsa.complexity_analysis", 100),
        ("python.core_syntax", 100),
        ("db.sql_querying", 100),
        ("behavioral.ownership", 100),
        ("sd.capacity_estimation", 75),
        ("bit_manipulation.core", 20),
    ]:
        assert gaps[key].priority == priority, key
    assert len(graph().dependents["dsa.complexity_analysis"]) == 5
    first = report.gaps[0]
    assert (first.skill_key, first.priority, first.tier, first.status) == (
        "behavioral.impact",
        100,
        "T1",
        "UNASSESSED",
    )
    assert (first.primary_gap_type, first.focus_stage) == ("UNASSESSED", "DIAGNOSE")
    assert report.top_assessed() == [] and report.feasibility_applied is False


def test_s02_strong_dsa_weak_system_design() -> None:
    world = background()
    for key in skills_where(component="system_design"):
        world.set(given(key, 3, 50, "MEDIUM"))
    comps = world.components()
    assert comps.score("system_design") == 43 and comps.weighted_score == 69
    report = world.gaps()
    gaps = report.by_skill()
    t1 = skills_where(component="system_design", tier="T1")
    assert len(t1) == 8
    assert {gap_summary(report, k) for k in t1} == {(37, 13500, 50, "HIGH", "LEVEL_UP", "TIMED")}
    assert gap_summary(report, "sd.capacity_estimation")[1:4] == (13500, 32, "MEDIUM")
    assert gap_summary(report, "sd.storage_search")[1:4] == (12000, 13, "LOW")
    assert gap_summary(report, "sd.distributed_coordination")[1:4] == (12000, 2, "NONE")
    assert gaps["sd.deep_dive_bottlenecks"].status != "BLOCKED"
    assert [g.skill_key for g in report.top_assessed()] == [
        "sd.caching",
        "sd.data_modeling",
        "sd.database_scaling",
    ]
    assert report.feasibility_applied and report.infeasible_components == ()
    assert not any(g.parked_reason for g in report.gaps)


def s03_world():  # type: ignore[no-untyped-def]
    world = background()
    world.evidence(
        "graph.traversal",
        [
            row(3, 100, 4, "F104", is_unseen=True, pattern_identified=True),
            row(3, 100, 10, "F105", is_unseen=True, pattern_identified=True),
            row(3, 0, 1, "F103", is_unseen=True, pattern_identified=False),
            row(3, 0, 3, "F102", is_unseen=True, pattern_identified=False),
            row(3, 0, 6, "F101", is_unseen=True, pattern_identified=False),
        ],
    )
    # Prior pattern rows + the §5.2 derived rows of the same 5 graph attempts (pattern identified or not).
    derived = [
        row(3, p, a, f"F10{i}", rule="DERIVED")
        for i, (p, a) in enumerate([(0, 6), (0, 3), (0, 1), (100, 4), (100, 10)], 1)
    ]
    prior = [row(5, 100, a, f"q{a}") for a in (10, 15, 20, 25, 30, 35)]
    world.evidence("dsa.pattern_recognition", prior + derived)
    for key in [
        "dp.fundamentals",
        "dp.knapsack_subset",
        "dp.strings_subsequence",
        "dp.grid_paths",
        "dp.interval_state_machine",
        "dp.tree",
    ]:
        world.set(declared_unknown(key))
    return world


def test_s03_weak_graph_pattern_recognition() -> None:  # also G1
    world = s03_world()
    s = world.states["graph.traversal"]
    assert (s.level, s.score, s.confidence, s.effective_score) == (3, 51, "MEDIUM", 44)
    p = world.states["dsa.pattern_recognition"]
    assert (p.level, p.score, p.confidence, p.effective_score) == (5, 79, "HIGH", 79)
    assert world.components().score("dsa") == 66
    report = world.gaps()
    g = report.by_skill()
    assert gap_summary(report, "graph.traversal") == (
        36,
        15900,
        57,
        "HIGH",
        "PATTERN_RECOGNITION",
        "PATTERN_DRILL",
    )
    assert g["graph.traversal"].reason_codes == (
        "LARGE_GAP",
        "BELOW_FLOOR",
        "HIGH_IMPORTANCE",
        "REPEATED_FAILURE",
        "GATE_FAILING",
        "PATTERN_MISIDENTIFIED",
    )
    assert len(g["graph.traversal"].evidence["PATTERN_MISIDENTIFIED"]) == 3
    dp = g["dp.fundamentals"]
    assert (dp.raw_gap, dp.pressure_bp, dp.priority, dp.status) == (80, 13500, 100, "CRITICAL")
    assert (dp.primary_gap_type, dp.focus_stage) == ("KNOWLEDGE", "LEARN")
    assert [r for r in dp.reason_codes if r.startswith("UNLOCKS:")] == [
        "UNLOCKS:dp.grid_paths",
        "UNLOCKS:dp.knapsack_subset",
        "UNLOCKS:dp.strings_subsequence",
    ]
    for key in ("dp.knapsack_subset", "dp.strings_subsequence", "dp.grid_paths"):
        assert (g[key].status, g[key].priority) == ("BLOCKED", 76), key
    assert (g["dp.tree"].status, g["dp.tree"].priority) == ("BLOCKED", 12)
    assert (g["dp.interval_state_machine"].status, g["dp.interval_state_machine"].priority) == ("BLOCKED", 12)
    assert (g["dsa.pattern_recognition"].priority, g["dsa.pattern_recognition"].status) == (1, "NONE")
    assert [x.skill_key for x in report.gaps[:2]] == ["dp.fundamentals", "graph.traversal"]


def test_s04_retention_decay() -> None:
    world = background()
    s = world.evidence(
        "binary_search.boundaries", [row(4, 100, 130, "a"), row(4, 100, 135, "b"), row(3, 100, 140, "c")]
    )
    assert (s.level, s.quality, s.score, s.confidence, s.effective_score, s.peak_score) == (
        1,
        Decimal(100),
        30,
        "LOW",
        15,
        72,
    )
    assert world.components().score("dsa") == 74
    report = world.gaps()
    g = report.by_skill()["binary_search.boundaries"]
    assert (g.raw_gap, g.severity, g.pressure_bp, g.priority, g.status) == (
        60,
        Decimal(45),
        12500,
        56,
        "HIGH",
    )
    assert (g.primary_gap_type, g.focus_stage) == ("RETENTION", "REINFORCE")
    assert {"DECAYED", "RETENTION_RISK", "BELOW_FLOOR"} <= set(g.reason_codes)
    assert report.gaps[0].skill_key == "binary_search.boundaries"


def test_s05_repeated_failure_leech() -> None:
    world = background()
    world.evidence(
        "db.isolation_mvcc",
        [
            row(3, 80, 41, "pa"),
            row(3, 75, 36, "pb"),
            row(3, 45, 16, "pc"),
            row(3, 30, 9, "pc"),
            row(3, 40, 1, "pc"),
        ],
    )
    world.revision["db.isolation_mvcc"] = RevisionFacts(max_active_lapses=0, has_leech=True)
    assert world.components().score("cs") == 73
    report = world.gaps()
    g = report.by_skill()["db.isolation_mvcc"]
    assert (g.raw_gap, g.severity, g.pressure_bp, g.priority, g.status) == (
        29,
        Decimal("21.75"),
        13900,
        30,
        "MEDIUM",
    )
    assert (g.primary_gap_type, g.focus_stage) == (
        "LEVEL_UP",
        "TIMED",
    ) and "REPEATED_FAILURE" in g.reason_codes
    assert [x.skill_key for x in report.top_assessed()] == ["db.isolation_mvcc"]


def test_s06_overconfidence() -> None:
    world = background()
    world.evidence(
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
    assert world.components().score("dsa") == 74
    report = world.gaps()
    assert gap_summary(report, "sliding_window.core") == (36, 13900, 50, "HIGH", "CONFIDENCE", "INDEPENDENT")
    assert "OVERCONFIDENT" in report.by_skill()["sliding_window.core"].reason_codes


def test_s07_underconfidence() -> None:
    world = background()
    world.evidence(
        "heap.top_k",
        [
            row(
                4,
                100,
                age,
                f"h{age}",
                self_rating_before=r,
                depth_points=60,
                timed=True,
                within_limit=True,
                time_ratio_bp=8000,
            )
            for age, r in ((3, 2), (6, 1), (10, 2))
        ],
    )
    report = world.gaps()
    g = report.by_skill()["heap.top_k"]
    assert gap_summary(report, "heap.top_k") == (15, 10000, 15, "LOW", "LEVEL_UP", "EXPLAIN")
    assert "UNDERCONFIDENT" in g.reason_codes and report.gaps[0].skill_key == "heap.top_k"


def test_s08_speed() -> None:
    world = background()
    world.evidence(
        "binary_search.basic",
        [
            row(3, 100, 3, "a", time_ratio_bp=48 * 10000 // 30),
            row(3, 100, 7, "b", time_ratio_bp=41 * 10000 // 30),
            row(3, 100, 11, "c", time_ratio_bp=52 * 10000 // 30),
        ],
    )
    report = world.gaps()
    assert gap_summary(report, "binary_search.basic") == (27, 11500, 31, "MEDIUM", "SPEED", "TIMED")
    g = report.by_skill()["binary_search.basic"]
    assert g.metrics["speed_median_ratio_bp"] == "16000.00" and "SPEED_BELOW_TARGET" in g.reason_codes


def test_s09_communication() -> None:
    world = background()
    world.evidence(
        "trees.traversal",
        [
            row(4, 100, a, f"t{a}", communication_points=c, depth_points=60)
            for a, c in ((2, 40), (5, 50), (8, 50))
        ],
    )
    world.evidence(
        "execution.think_aloud",
        [
            row(4, p, a, f"t{a}", rule="DERIVED", communication_points=p)
            for a, p in ((2, 40), (5, 50), (8, 50))
        ],
    )
    comps = world.components()
    assert (comps.score("coding"), comps.score("dsa")) == (67, 75)
    report = world.gaps()
    # D-061: 3 of the last 5 rows < 60 -> FAILURE 2400 on top of GATE + FLOOR.
    assert gap_summary(report, "execution.think_aloud") == (
        75,
        15900,
        89,
        "CRITICAL",
        "COMMUNICATION",
        "THINK_ALOUD",
    )
    assert gap_summary(report, "trees.traversal")[2:] == (15, "LOW", "COMMUNICATION", "THINK_ALOUD")


def test_s10_prerequisite_blocking() -> None:
    world = background()
    world.set(given("dp.fundamentals", 1, 25, "MEDIUM"))
    world.set(given("recursion.fundamentals", 3, 50, "MEDIUM"))
    assert world.components().score("dsa") == 72
    report = world.gaps()
    g = report.by_skill()
    dp = g["dp.fundamentals"]
    assert (dp.raw_gap, dp.pressure_bp, dp.priority, dp.status, dp.primary_gap_type) == (
        62,
        11500,
        71,
        "BLOCKED",
        "PREREQUISITE",
    )
    assert dp.focus_skill == "recursion.fundamentals"
    rec = g["recursion.fundamentals"]
    assert (rec.priority, rec.status, rec.primary_gap_type, rec.focus_stage) == (
        64,
        "CRITICAL",
        "LEVEL_UP",
        "TIMED",
    )
    assert "UNLOCKS:dp.fundamentals" in rec.reason_codes
    assert g["backtracking.core"].status != "BLOCKED"
    assert report.gaps[0].skill_key == "recursion.fundamentals"


def test_s11_overdue_revisions_mark_reason_only() -> None:
    world = background()
    world.revision["binary_search.basic"] = RevisionFacts(has_overdue_item=True)
    g = world.gaps().by_skill()["binary_search.basic"]
    assert g.status == "NONE" and "OVERDUE_REVISION" in g.reason_codes


def test_s12_infeasible_deadline() -> None:
    world = background(target_date=date(2027, 1, 11))
    for key in skills_where(component="lld"):
        world.set(given(key, 2, 35, "LOW"))
    comps = world.components()
    assert comps.score("lld") == 20 and comps.weighted_score == 68
    report = world.gaps()
    assert (report.phase, report.weeks_left) == ("CONSOLIDATE", Decimal(10))
    g = report.by_skill()
    req = g["lld.requirements_entities"]
    assert (req.priority, req.status, req.primary_gap_type, req.focus_stage) == (
        81,
        "CRITICAL",
        "PRACTICE",
        "INDEPENDENT",
    )
    assert "UNLOCKS:lld.class_design" in req.reason_codes
    assert (g["lld.class_design"].status, g["lld.class_design"].priority) == ("BLOCKED", 81)
    assert (g["lld.machine_coding"].status, g["lld.machine_coding"].priority) == ("BLOCKED", 81)
    parked = [
        k
        for k in ("lld.concurrency_safety", "lld.design_patterns", "lld.extensibility")
        if g[k].parked_reason == "NOT_FEASIBLE"
    ]
    assert parked == ["lld.concurrency_safety", "lld.design_patterns", "lld.extensibility"]
    assert report.infeasible_components == ("lld",)
    assert report.feasibility["lld"] == (900, 750)
    assert report.gaps[0].skill_key == "lld.requirements_entities"


def test_s13_build_phase_new_topics() -> None:
    world = background()
    world.set(declared_unknown("trie.core"))
    world.set(declared_unknown("os.memory_virtual"))
    comps = world.components()
    assert (comps.score("dsa"), comps.score("cs")) == (75, 73)
    report = world.gaps()
    for key in ("trie.core", "os.memory_virtual"):
        g = report.by_skill()[key]
        assert (g.raw_gap, g.severity, g.priority, g.status, g.primary_gap_type, g.focus_stage) == (
            65,
            Decimal("32.5"),
            33,
            "MEDIUM",
            "KNOWLEDGE",
            "LEARN",
        )
    assert [g.skill_key for g in report.top_assessed(2)] == ["os.memory_virtual", "trie.core"]


def test_s14_consolidate_parking() -> None:
    world = background(target_date=date(2027, 1, 11))
    world.evidence(
        "trie.core", [row(0, 0, 3, "study", is_scoring=False, kind="STUDY_SESSION", study_minutes=45)]
    )
    world.set(declared_unknown("trie.core"), world.facts["trie.core"])
    world.set(given("sd.storage_search", 2, 45, "LOW", effective=30))
    report = world.gaps()
    g = report.by_skill()
    parked = {k for k, x in g.items() if x.status == "PARKED"}
    assert parked == set(skills_where(tier="T4")) | {"trie.core"}
    assert all(g[k].parked_reason == "PARKED_DEADLINE" for k in parked)
    assert "STUDIED_NOT_TESTED" in g["trie.core"].reason_codes
    assert gap_summary(report, "sd.storage_search")[2:] == (18, "LOW", "PRACTICE", "INDEPENDENT")
    assert report.infeasible_components == () and report.top_assessed()[0].skill_key == "sd.storage_search"


def test_s15_sharpen_parking() -> None:
    world = background(target_date=date(2026, 11, 23))
    world.set(given("heap.two_heaps_merge_k", 2, 40, "LOW", effective=25))
    world.set(given("graph.shortest_path", 1, 25, "LOW", effective=10))
    world.set(given("execution.time_management", 4, 66, "MEDIUM"))
    report = world.gaps()
    assert (report.phase, report.weeks_left) == ("SHARPEN", Decimal(3))
    parked = {k for k, x in report.by_skill().items() if x.status == "PARKED"}
    assert parked == set(skills_where(tier="T4")) | {"heap.two_heaps_merge_k", "graph.shortest_path"}
    assert gap_summary(report, "execution.time_management")[2:] == (12, "LOW", "LEVEL_UP", "EXPLAIN")


def test_s16_parked_skill_still_counts() -> None:
    world = background(target_date=date(2027, 1, 11))
    world.set(given("db.nosql_tradeoffs", 1, 20, "LOW"))
    assert world.components().score("cs") == 73
    report = world.gaps()
    assert report.by_skill()["db.nosql_tradeoffs"].status == "PARKED"
    assert report.top_assessed() == []


def mock_world(key: str, prior: list, mock_points: int):  # type: ignore[no-untyped-def,type-arg]
    rounds = [
        MockRoundSummary(100, date(2026, 11, 1), (key,)),
        MockRoundSummary(13, date(2026, 10, 28), ()),
        MockRoundSummary(12, date(2026, 10, 26), ()),
    ]
    weak = mock_weakness_skills(rounds, date(2026, 11, 2), v1)
    world = background()
    world.evidence(
        key, [*prior, row(7, mock_points, 1, "mock_round:100", is_weakness=True)], mock_weakness=key in weak
    )
    return world


def test_s17_mock_weakness() -> None:
    capacity_prior = [
        row(5, 100, 10, "a"),
        row(5, 100, 20, "b"),
        row(4, 100, 30, "c"),
        row(4, 100, 40, "d"),
        row(3, 100, 50, "e"),
        row(4, 60, 25, "f"),
    ]
    world = mock_world("sd.capacity_estimation", capacity_prior, 40)
    caching = [row(5, 100, a, f"c{a}") for a in (8, 16, 24)] + [
        row(4, 100, 32, "d"),
        row(4, 100, 40, "e"),
        row(3, 100, 50, "f"),
    ]
    world.evidence(
        "sd.caching", [*caching, row(7, 55, 1, "mock_round:100", is_weakness=True)], mock_weakness=True
    )
    s = world.states["sd.capacity_estimation"]
    assert (s.level, s.score, s.effective_score, s.reality_capped) == (5, 40, 40, True)
    assert world.states["sd.caching"].score == 55
    assert world.components().score("system_design") == 73
    report = world.gaps()
    assert gap_summary(report, "sd.capacity_estimation") == (
        35,
        13000,
        34,
        "MEDIUM",
        "INTERVIEW_EXECUTION",
        "SIMULATE",
    )
    assert gap_summary(report, "sd.caching") == (25, 13000, 33, "MEDIUM", "INTERVIEW_EXECUTION", "SIMULATE")
    assert {"MOCK_WEAKNESS", "BELOW_FLOOR"} <= set(report.by_skill()["sd.caching"].reason_codes)
    assert [g.skill_key for g in report.top_assessed(2)] == ["sd.capacity_estimation", "sd.caching"]


def test_s18_behavioral_weakness() -> None:
    world = background()
    keys = ["behavioral.ownership", "behavioral.impact", "communication.structured_answers"]
    for key in keys:
        world.set(given(key, 2, 40, "MEDIUM"))
    comps = world.components()
    assert (comps.score("behavioral"), comps.weighted_score) == (59, 74)
    report = world.gaps()
    for key in keys:
        assert gap_summary(report, key) == (47, 13500, 63, "CRITICAL", "PRACTICE", "INDEPENDENT"), key
    assert [g.skill_key for g in report.top_assessed()] == sorted(keys)


def test_s19_final_simulation_weakness() -> None:
    prior = [row(5, 100, a, f"d{a}") for a in (9, 19, 44)] + [
        row(4, 100, 29, "e"),
        row(4, 100, 35, "f"),
        row(3, 100, 55, "g"),
    ]
    world = mock_world("sd.deep_dive_bottlenecks", prior, 55)
    assert world.states["sd.deep_dive_bottlenecks"].effective_score == 55
    assert world.components().score("system_design") == 74
    report = world.gaps()
    assert gap_summary(report, "sd.deep_dive_bottlenecks") == (
        25,
        13000,
        33,
        "MEDIUM",
        "INTERVIEW_EXECUTION",
        "SIMULATE",
    )
    assert report.top_assessed()[0].skill_key == "sd.deep_dive_bottlenecks"


def test_gap_report_is_deterministic_under_input_order() -> None:
    world = s03_world()
    first = world.gaps()
    world.states = dict(reversed(list(world.states.items())))
    world.facts = dict(reversed(list(world.facts.items())))
    assert world.gaps() == first
    assert replace(first) == first
