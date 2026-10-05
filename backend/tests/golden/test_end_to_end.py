"""End-to-end chain on the golden scenarios: evidence/state -> components -> gaps -> readiness (computed) ->
mentor plan + message. Readiness is NOT given here; it comes from the readiness engine, converted exactly as
the production plan service converts it."""

from __future__ import annotations

from datetime import date

from app.domain.mentor.model import ReadinessView
from app.domain.readiness.engine import MockRound
from app.domain.revision.model import RevisionHealth
from app.services.mentor_service import Outputs, RunResult
from app.services.plan_service import readiness_view
from tests.golden.harness import (
    background,
    cold_start,
    final_sim,
    given,
    m_ok_rounds,
    plan,
    profile,
    readiness,
    skills_where,
)


def view(world, **kwargs) -> ReadinessView:  # type: ignore[no-untyped-def]
    r = readiness(world, **kwargs)
    result = RunResult(
        0, world.as_of, "v1", "seed-v1", "", 0, {}, [], outputs=Outputs([], {}, None, None, readiness=r)
    )
    return readiness_view(result)


def test_s01_cold_start_chain() -> None:
    w = cold_start()
    w.battery_done = set()
    w.readiness = view(w, rounds=[], health=RevisionHealth(0, (), None, 0, 0), recent=set())
    assert w.readiness.state == "NOT_MEASURED"
    assert plan(w).message.rule == "CALIBRATION"


def test_s02_and_s18_readiness_blocker_messages_from_computed_readiness() -> None:
    s02 = background()
    for key in skills_where(component="system_design"):
        s02.set(given(key, 3, 50, "MEDIUM"))
    s02.track_minutes = {**profile().track_minutes, "system_design": 30}
    s02.readiness = view(s02)
    assert plan(s02).message.text == "FOUNDATION: System Design 43 < 45. Today's work targets it: sd.caching."

    s18 = background()
    for key in ["behavioral.ownership", "behavioral.impact", "communication.structured_answers"]:
        s18.set(given(key, 2, 40, "MEDIUM"))
    s18.track_minutes = {**profile().track_minutes, "behavioral_project": 10}
    s18.readiness = view(s18)
    assert (
        plan(s18).message.text
        == "FOUNDATION: behavioral.impact level L2 < L3. Today's work targets it: behavioral.impact."
    )


def test_s10_and_s12_chains() -> None:
    s10 = background()
    s10.set(given("dp.fundamentals", 1, 25, "MEDIUM"))
    s10.set(given("recursion.fundamentals", 3, 50, "MEDIUM"))
    s10.readiness = view(s10)
    assert s10.readiness.state == "FOUNDATION"
    assert plan(s10).message.rule == "PREREQUISITE_UNLOCK"

    s12 = background(target_date=date(2027, 1, 11))
    for key in skills_where(component="lld"):
        s12.set(given(key, 2, 35, "LOW"))
    s12.readiness = view(s12)
    assert plan(s12).message.rule == "DEADLINE_INFEASIBLE"


def test_s15_sharpen_mock_from_computed_readiness() -> None:
    w = background(target_date=date(2026, 11, 23))
    w.set(given("heap.two_heaps_merge_k", 2, 40, "LOW", effective=25))
    w.set(given("graph.shortest_path", 1, 25, "LOW", effective=10))
    w.set(given("execution.time_management", 4, 66, "MEDIUM"))
    rounds = [
        r
        if r.round_type != "BEHAVIORAL"
        else MockRound(r.id, r.mock_id, date(2026, 10, 15), "BEHAVIORAL", r.source, r.round_score)
        for r in m_ok_rounds()
    ]
    w.readiness = view(w, rounds=rounds)
    assert (w.readiness.state, w.readiness.simulation_eligible) == ("DEVELOPING", True)


def test_s20_ready_maintain_from_computed_readiness() -> None:
    sims = [
        final_sim(1, date(2026, 10, 11), "PEER", "LLD"),
        final_sim(2, date(2026, 10, 18), "PEER", "SYSTEM_DESIGN"),
        final_sim(3, date(2026, 10, 25), "SELF", "SYSTEM_DESIGN"),
    ]
    from tests.golden.harness import F0
    from tests.golden.test_plan_scenarios import M_OK
    from tests.golden.test_revision_scenarios import item

    w = background()
    w.readiness = view(w, sims=sims)
    assert w.readiness.state == "INTERVIEW_READY"
    w.mock_rounds = list(M_OK)
    w.revision_items = {
        "CS:db.indexing": item("CS:db.indexing", "db.indexing", "CS", 10, F0),
        "PATTERN:heap.top_k": item("PATTERN:heap.top_k", "heap.top_k", "PATTERN", 10, F0),
    }
    assert plan(w).message.rule == "READY_MAINTAIN"
