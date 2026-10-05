"""Readiness expectations of SCENARIOS.md S01-S20 and the READINESS_MODEL §9 worked example (pure, real seed)."""

from __future__ import annotations

from datetime import date

from app.domain.gaps.model import RevisionFacts
from app.domain.readiness.components import ComponentScore, ComponentScores
from app.domain.readiness.engine import MockRound, calculate_readiness
from app.domain.revision.model import RevisionHealth
from tests.golden.harness import (
    R_OK,
    background,
    cold_start,
    declared_unknown,
    final_sim,
    given,
    graph,
    m_ok_rounds,
    profile,
    readiness,
    skills_where,
)
from tests.golden.test_gap_scenarios import mock_world, s03_world
from tests.scenario_support import row


def msgs(conditions) -> list[str]:  # type: ignore[no-untyped-def]
    return [f"{c.gate} {c.message}" for c in conditions]


G9_NONE = "G9 0 of 3 final simulations"


def test_bg_is_developing_with_only_g9() -> None:
    r = readiness(background())
    assert (r.state, r.weighted_score, r.simulation_eligible, r.lapsed) == ("DEVELOPING", 75, True, False)
    assert msgs(r.blockers) == [G9_NONE]


def test_s01_not_measured() -> None:
    r = readiness(cold_start(), rounds=[], health=RevisionHealth(0, (), None, 0, 0), recent=set())
    assert (r.state, r.weighted_score) == ("NOT_MEASURED", 0)
    assert [c.subject for c in r.blockers] == [
        "behavioral",
        "coding",
        "cs",
        "dsa",
        "lld",
        "project",
        "system_design",
    ]
    assert r.blockers[0].message == "Behavioral assessed 0% < 70%"


def test_s02_foundation_by_system_design() -> None:
    w = background()
    for key in skills_where(component="system_design"):
        w.set(given(key, 3, 50, "MEDIUM"))
    r = readiness(w)
    assert (r.state, r.weighted_score, r.limiting_component) == ("FOUNDATION", 69, "system_design")
    assert msgs(r.blockers) == ["G1 System Design 43 < 45"] and r.blockers[0].deficit == 2
    failing = msgs(r.all_failing)
    assert "G2 System Design 43 < 72" in failing and G9_NONE in failing
    assert len([c for c in r.all_failing if c.gate == "G4"]) == 8


def test_s03_foundation_by_declared_unknown_t1() -> None:
    r = readiness(s03_world())
    assert (r.state, r.weighted_score) == ("FOUNDATION", 73)
    assert msgs(r.blockers) == ["G1 dp.fundamentals level L0 < L3"]


def test_s04_s07_s13_s14_s15_s16_developing_with_g9_only() -> None:
    s04 = background()
    s04.evidence(
        "binary_search.boundaries", [row(4, 100, 130, "a"), row(4, 100, 135, "b"), row(3, 100, 140, "c")]
    )
    s07 = background()
    s07.evidence(
        "heap.top_k",
        [
            row(4, 100, a, f"h{a}", self_rating_before=r_, depth_points=60)
            for a, r_ in ((3, 2), (6, 1), (10, 2))
        ],
    )
    s13 = background()
    s13.set(declared_unknown("trie.core"))
    s13.set(declared_unknown("os.memory_virtual"))
    s14 = background(target_date=date(2027, 1, 11))
    s14.set(declared_unknown("trie.core"))
    s14.set(given("sd.storage_search", 2, 45, "LOW", effective=30))
    s15 = background(target_date=date(2026, 11, 23))
    s15.set(given("heap.two_heaps_merge_k", 2, 40, "LOW", effective=25))
    s15.set(given("graph.shortest_path", 1, 25, "LOW", effective=10))
    s15.set(given("execution.time_management", 4, 66, "MEDIUM"))
    s16 = background(target_date=date(2027, 1, 11))
    s16.set(given("db.nosql_tradeoffs", 1, 20, "LOW"))
    for name, w in [("S04", s04), ("S07", s07), ("S13", s13), ("S14", s14), ("S15", s15), ("S16", s16)]:
        r = readiness(w)
        assert (r.state, msgs(r.blockers)) == ("DEVELOPING", [G9_NONE]), name
    assert readiness(s15).simulation_eligible is True


def test_s05_pass_rate_80() -> None:
    w = background()
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
    w.revision["db.isolation_mvcc"] = RevisionFacts(has_leech=True)
    r = readiness(w, health=RevisionHealth(0, (), 80, 21, 17))  # 17/21 = 80%
    assert (r.state, msgs(r.blockers)) == ("DEVELOPING", [G9_NONE])


def test_s06_critical_skill_and_overdue_revisions() -> None:
    w = background()
    w.evidence(
        "sliding_window.core",
        [
            row(3, 100, 20, "a", self_rating_before=3),
            row(3, 100, 25, "b", self_rating_before=3),
            row(3, 0, 2, "c", self_rating_before=5),
            row(3, 0, 5, "d", self_rating_before=4),
            row(3, 0, 9, "e", self_rating_before=5),
            row(3, 50, 12, "f", self_rating_before=4),
        ],
    )
    r = readiness(w, health=RevisionHealth(2, ("PROBLEM:F205", "PROBLEM:F206"), 85, 20, 17))
    assert msgs(r.blockers) == [
        "G4 sliding_window.core effective 44 < 65 / sliding_window.core level L3 < L4",
        "G7 overdue T1/T2 > 7 days: 2",
        G9_NONE,
    ]


def test_s08_speed_gap_blockers() -> None:
    w = background()
    w.evidence("binary_search.basic", [row(3, 100, 3, "a"), row(3, 100, 7, "b"), row(3, 100, 11, "c")])
    r = readiness(w, health=RevisionHealth(1, ("PROBLEM:F303",), 85, 20, 17))
    assert msgs(r.blockers) == [
        "G4 binary_search.basic effective 53 < 65 / binary_search.basic level L3 < L4",
        "G7 overdue T1/T2 > 7 days: 1",
        G9_NONE,
    ]


def test_s09_coding_gate_and_critical_gap() -> None:
    w = background()
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
    r = readiness(w)
    assert msgs(r.blockers) == ["G2 Coding & Execution 67 < 70", "G5 execution.think_aloud CRITICAL", G9_NONE]


def test_s10_foundation_by_dp() -> None:
    w = background()
    w.set(given("dp.fundamentals", 1, 25, "MEDIUM"))
    w.set(given("recursion.fundamentals", 3, 50, "MEDIUM"))
    r = readiness(w)
    assert (r.state, msgs(r.blockers)) == ("FOUNDATION", ["G1 dp.fundamentals level L1 < L3"])


def test_s11_overdue_revision_gate() -> None:
    r = readiness(background(), health=RevisionHealth(13, (), 85, 20, 17))  # D-065: 6 + 4 + 3
    assert msgs(r.blockers) == ["G7 overdue T1/T2 > 7 days: 13", G9_NONE]


def test_s12_lld_foundation() -> None:
    w = background(target_date=date(2027, 1, 11))
    for key in skills_where(component="lld"):
        w.set(given(key, 2, 35, "LOW"))
    r = readiness(w)
    assert (r.state, r.weighted_score) == ("FOUNDATION", 68)
    assert msgs(r.blockers) == [
        "G1 LLD / OOD 20 < 45",
        "G1 lld.class_design level L2 < L3",
        "G1 lld.machine_coding level L2 < L3",
        "G1 lld.requirements_entities level L2 < L3",
    ]


def test_s17_mock_weakness_blocks_g4_g6() -> None:
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
    rounds = [*m_ok_rounds(), MockRound(200, 200, date(2026, 11, 1), "SYSTEM_DESIGN", "PEER", 58)]
    r = readiness(w, rounds=rounds)
    assert msgs(r.blockers) == [
        "G4 sd.caching effective 55 < 65",
        "G6 SYSTEM_DESIGN latest round 58 < 65",
        G9_NONE,
    ]
    assert r.simulation_eligible is False


def test_s18_behavioral_foundation() -> None:
    w = background()
    keys = ["behavioral.ownership", "behavioral.impact", "communication.structured_answers"]
    for key in keys:
        w.set(given(key, 2, 40, "MEDIUM"))
    r = readiness(w)
    assert (r.state, r.weighted_score) == ("FOUNDATION", 74)
    assert msgs(r.blockers) == [f"G1 {k} level L2 < L3" for k in sorted(keys)]
    failing = msgs(r.all_failing)
    assert "G2 Behavioral 59 < 70" in failing and G9_NONE in failing
    assert (
        len([c for c in r.all_failing if c.gate == "G4"]) == 3
        and len([c for c in r.all_failing if c.gate == "G5"]) == 3
    )


def test_s19_failed_final_simulation() -> None:
    prior = [row(5, 100, a, f"d{a}") for a in (9, 19, 44)] + [
        row(4, 100, 29, "e"),
        row(4, 100, 35, "f"),
        row(3, 100, 55, "g"),
    ]
    w = mock_world("sd.deep_dive_bottlenecks", prior, 55)
    sims = [
        final_sim(1, date(2026, 10, 18), "PEER", "LLD"),
        final_sim(2, date(2026, 10, 25), "SELF", "SYSTEM_DESIGN"),
        final_sim(
            3,
            date(2026, 11, 1),
            "PEER",
            "SYSTEM_DESIGN",
            {"DSA": 82, "SYSTEM_DESIGN": 66, "BEHAVIORAL": 78, "PROJECT_DEEP_DIVE": 74, "CS": 80},
        ),
    ]
    r = readiness(w, sims=sims)
    assert msgs(r.blockers) == [
        "G4 sd.deep_dive_bottlenecks effective 55 < 65",
        "G9 final simulation 2026-11-01 failed: SYSTEM_DESIGN 66 < 70",
    ]
    assert r.simulation_eligible is False and not [c for c in r.all_failing if c.gate == "G6"]


def test_s20_interview_ready_not_strong() -> None:
    sims = [
        final_sim(1, date(2026, 10, 11), "PEER", "LLD"),
        final_sim(2, date(2026, 10, 18), "PEER", "SYSTEM_DESIGN"),
        final_sim(3, date(2026, 10, 25), "SELF", "SYSTEM_DESIGN"),
    ]
    r = readiness(background(), sims=sims)
    assert (r.state, r.blockers, r.simulation_eligible) == ("INTERVIEW_READY", (), True)
    assert [c["score"] for c in r.components] == [76, 73, 75, 77, 76, 75, 73]


def test_lapsed_and_strong_need_snapshots() -> None:
    previous = {date(2026, 10, 20): "INTERVIEW_READY"}
    assert readiness(background(), previous=previous).lapsed is True
    assert readiness(background()).lapsed is False


def test_worked_example_weighted_score_cannot_hide_a_weak_component() -> None:
    scores = {
        "dsa": 90,
        "coding": 75,
        "cs": 85,
        "lld": 75,
        "system_design": 42,
        "behavioral": 90,
        "project": 75,
    }
    base = background()
    comps = ComponentScores(
        {k: ComponentScore(k, v, 100, 100, 10) for k, v in scores.items()}, 76, "system_design"
    )
    r = calculate_readiness(
        components=comps,
        states=base.states,
        gap_report=base.gaps(),
        graph=graph(),
        profile=profile(),
        mock_rounds=m_ok_rounds(),
        final_simulations=[],
        revision_health=R_OK,
        recent_components={c.key for c in profile().components},
        previous_states={},
        as_of_date=base.as_of,
    )
    assert (r.state, r.weighted_score, r.limiting_component) == ("FOUNDATION", 76, "system_design")
    assert msgs(r.blockers) == ["G1 System Design 42 < 45"]
    assert "G2 System Design 42 < 72" in msgs(r.all_failing)
