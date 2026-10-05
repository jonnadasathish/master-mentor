"""Golden-scenario harness (SCENARIOS.md §0): the real seed catalog + F0/BG fixtures, pure domain only.

States are either *given* (scenario "at L3, score 50, MEDIUM") or *derived* from rows through the real
evidence/state engines. Every engine runs with an explicit ``as_of_date`` (F0 = 2026-11-02) and ruleset v1.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from app.domain.baseline.calibration import BatteryItem, calibration_status
from app.domain.catalog.model import Catalog
from app.domain.catalog.validate import validate_seed
from app.domain.evidence.model import EvidenceRow
from app.domain.gaps.engine import calculate_gaps
from app.domain.gaps.facts import build_skill_facts
from app.domain.gaps.model import GapReport, RevisionFacts, SkillFacts
from app.domain.mentor.model import (
    DailyPlan,
    MockRoundInfo,
    PlanInputs,
    PracticeSummary,
    ProblemInfo,
    ReadinessView,
)
from app.domain.mentor.planner import generate_daily_plan
from app.domain.profile.model import Goal, ProfileSpec, SkillGraph, from_catalog
from app.domain.readiness.components import ComponentScores, calculate_component_scores
from app.domain.revision.model import RevisionItem, RevisionProjection
from app.domain.rulesets import v1
from app.domain.skills.state import SkillState, calculate_skill_state
from app.infrastructure.seed_files import read_seed

SEED_DIR = Path(__file__).resolve().parents[3] / "seed"
F0 = date(2026, 11, 2)
F0_TARGET = date(2027, 6, 28)
BG_TIERS = {"T1": (5, 80), "T2": (5, 75), "T3": (4, 65), "T4": (3, 50)}
BG_DAYS_SINCE_PRACTICE = {"T1": 3, "T2": 3, "T3": 3, "T4": 40}


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    raw, lock = read_seed(SEED_DIR)
    result = validate_seed(raw, lock)
    assert result.catalog is not None, result.errors
    return result.catalog


@lru_cache(maxsize=1)
def graph_and_profile() -> tuple[SkillGraph, ProfileSpec]:
    return from_catalog(catalog())


def graph() -> SkillGraph:
    return graph_and_profile()[0]


def profile() -> ProfileSpec:
    return graph_and_profile()[1]


def given(
    key: str,
    level: int,
    score: int,
    confidence: str,
    *,
    effective: int | None = None,
    peak: int | None = None,
    declared_unknown: bool = False,
) -> SkillState:
    """A scenario-stated state ("L3, score 50, MEDIUM"); effective = score - uncertainty unless given."""
    eff = effective if effective is not None else max(score - int(v1.UNCERTAINTY[confidence]), 0)
    label = "UNASSESSED"
    for name, minimum in v1.SKILL_LABELS:
        if eff >= minimum:
            label = str(name)
            break
    return SkillState(
        key, score, level, None, confidence, eff, peak if peak is not None else score, 0, 0,
        None, None, label, False, declared_unknown, (), (),
    )  # fmt: skip


def declared_unknown(key: str) -> SkillState:
    return given(key, 0, 0, "LOW", effective=0, declared_unknown=True)


def unassessed(key: str) -> SkillState:
    return SkillState(
        key, None, None, None, "NONE", None, None, 0, 0, None, None, "UNASSESSED", False, False, (), ()
    )


@dataclass
class World:
    """Mutable scenario under construction; ``gaps()`` runs the engines."""

    as_of: date = F0
    target_date: date | None = F0_TARGET
    states: dict[str, SkillState] = field(default_factory=dict)
    facts: dict[str, SkillFacts] = field(default_factory=dict)
    revision: dict[str, RevisionFacts] = field(default_factory=dict)
    rows: dict[str, list[EvidenceRow]] = field(default_factory=dict)
    # plan inputs (MENTOR_ENGINE §1)
    readiness: ReadinessView = field(default_factory=ReadinessView)
    revision_items: dict[str, RevisionItem] = field(default_factory=dict)
    mock_rounds: list[MockRoundInfo] = field(
        default_factory=lambda: [MockRoundInfo(1, "DSA", date(2026, 10, 28))]
    )
    track_minutes: dict[str, int] | None = None  # None = every track at its weekly allocation (BG)
    skill_minutes_7d: dict[str, int] = field(default_factory=dict)
    study_minutes_7d: dict[str, int] = field(default_factory=dict)
    extra_problems: list[ProblemInfo] = field(default_factory=list)
    attempts: dict[int, tuple[int, date]] = field(default_factory=dict)  # problem id -> (count, last)
    battery_done: set[str] | None = None  # None = complete
    triage_suspended: tuple[str, ...] = ()
    budget: int = 90

    def set(self, state: SkillState, facts: SkillFacts | None = None) -> World:
        self.states[state.skill] = state
        if facts is not None:
            self.facts[state.skill] = facts
        return self

    def evidence(self, key: str, rows: Iterable[EvidenceRow], *, mock_weakness: bool = False) -> SkillState:
        """Replace a skill's background with real rows through the evidence engines."""
        own = [replace(r, skill=key) for r in rows]
        self.rows[key] = own
        state = calculate_skill_state(key, own, self.as_of, v1)
        self.states[key] = state
        self.facts[key] = build_skill_facts(own, self.as_of, v1, mock_weakness=mock_weakness)
        return state

    def components(self) -> ComponentScores:
        return calculate_component_scores(self.states, graph(), profile())

    def gaps(self, components: ComponentScores | None = None) -> GapReport:
        return calculate_gaps(
            skill_states=self.states,
            component_scores=components or self.components(),
            profile=profile(),
            graph=graph(),
            skill_facts=self.facts,
            revision_facts=self.revision,
            goal=Goal(None, self.target_date, (90, 90, 90, 90, 90, 75, 75)),
            as_of_date=self.as_of,
            ruleset=v1,
        )


def background(**kwargs: object) -> World:
    """F0 + BG: every skill at its tier target with HIGH confidence, practiced 3 days ago (T4: 40)."""
    world = World(**kwargs)  # type: ignore[arg-type]
    for key, spec in graph().skills.items():
        level, score = BG_TIERS[spec.tier]
        world.states[key] = given(key, level, score, "HIGH")
        world.facts[key] = SkillFacts(
            days_since_last_practice=BG_DAYS_SINCE_PRACTICE[spec.tier], scoring_rows=6
        )
    return world


def cold_start(**kwargs: object) -> World:
    world = World(**kwargs)  # type: ignore[arg-type]
    for key in graph().skills:
        world.states[key] = unassessed(key)
    return world


def skills_where(**match: object) -> list[str]:
    return [k for k, s in graph().skills.items() if all(getattr(s, f) == v for f, v in match.items())]


def gap_summary(report: GapReport, key: str) -> tuple[object, ...]:
    g = report.by_skill()[key]
    return (g.raw_gap, g.pressure_bp, g.priority, g.status, g.primary_gap_type, g.focus_stage)


def as_mapping(report: GapReport) -> Mapping[str, object]:
    return report.by_skill()


def seed_problems(world: World) -> tuple[ProblemInfo, ...]:
    out = []
    for p in catalog().problems:
        count, last = world.attempts.get(p.id, (0, None))
        out.append(
            ProblemInfo(
                p.id, p.platform_key, p.difficulty, p.is_canonical,
                tuple((s.skill, s.mapping_weight_bp) for s in p.skills), count, last,
            )
        )  # fmt: skip
    return (*out, *world.extra_problems)


def plan(world: World) -> DailyPlan:
    report = world.gaps()
    battery = [
        BatteryItem(b.key, b.position, b.name, b.minutes, b.observation_kind, b.covers)
        for b in catalog().baseline
    ]
    done = {b.key for b in battery} if world.battery_done is None else world.battery_done
    required = [k for k, sp in graph().skills.items() if sp.required]
    calibration = calibration_status(
        battery=battery,
        completed_keys=done,
        required_skills=required,
        assessed_skills={k for k, st in world.states.items() if st.assessed},
        ruleset=v1,
    )
    tracks = dict(profile().track_minutes) if world.track_minutes is None else world.track_minutes
    inputs = PlanInputs(
        as_of=world.as_of,
        budget=world.budget,
        phase=report.phase,
        weeks_left=report.weeks_left,
        target_date=world.target_date,
        goal_exists=True,
        calibration=calibration,
        gaps=report,
        states=world.states,
        facts=world.facts,
        components=world.components(),
        graph=graph(),
        profile=profile(),
        revision=RevisionProjection(dict(world.revision_items), ()),
        templates=catalog().templates,
        problems=seed_problems(world),
        milestones=catalog().milestones,
        readiness=world.readiness,
        practice=PracticeSummary(
            track_minutes_7d=tracks,
            skill_minutes_7d={**world.skill_minutes_7d, **world.study_minutes_7d},
            study_minutes_7d=world.study_minutes_7d,
        ),
        mock_rounds=tuple(world.mock_rounds),
        triage_suspended_today=world.triage_suspended,
    )
    return generate_daily_plan(inputs, v1)


def summary(p: DailyPlan) -> list[tuple[str, str | None, str | None, int]]:
    return [(i.candidate_key, i.template_key, i.stage, i.minutes) for i in p.items]


# ------------------------------------------------------------------------------------------- readiness
from app.domain.readiness.engine import (  # noqa: E402
    FinalSimulation,
    MockRound,
    Readiness,
    calculate_readiness,
)
from app.domain.revision.model import RevisionHealth  # noqa: E402

R_OK = RevisionHealth(
    overdue_t1_t2_over_7d=0, overdue_items=(), pass_rate_30d=85, reviews_30d=20, passes_30d=17
)


def m_ok_rounds() -> list[MockRound]:
    """F0 M-OK: 14 rounds in 60 days (DSA 4, others 2), >= 1 PEER per type; last 6 = 78,76,75,77,74,76."""
    latest = [
        ("DSA", date(2026, 10, 28), 78),
        ("CS", date(2026, 10, 26), 76),
        ("PROJECT_DEEP_DIVE", date(2026, 10, 25), 75),
        ("BEHAVIORAL", date(2026, 10, 24), 77),
        ("LLD", date(2026, 10, 22), 74),
        ("SYSTEM_DESIGN", date(2026, 10, 20), 76),
    ]
    rounds = [MockRound(100 + n, 100 + n, d, rt, "PEER", s) for n, (rt, d, s) in enumerate(latest)]
    older = ["DSA", "DSA", "DSA", "CS", "PROJECT_DEEP_DIVE", "BEHAVIORAL", "LLD", "SYSTEM_DESIGN"]
    rounds += [
        MockRound(50 + n, 50 + n, date(2026, 10, 1) - timedelta(days=n), rt, "SELF", 70)
        for n, rt in enumerate(older)
    ]
    return rounds


def final_sim(
    mock_id: int, day: date, source: str, extra: str, scores: dict[str, int] | None = None
) -> FinalSimulation:
    types = ["DSA", "CS", "BEHAVIORAL", "PROJECT_DEEP_DIVE", extra]
    scores = scores or {}
    rounds = tuple(
        MockRound(mock_id * 10 + n, mock_id, day, rt, source, scores.get(rt, 76), order=n)
        for n, rt in enumerate(types)
    )
    return FinalSimulation(mock_id, day, source, rounds)


def readiness(
    world: World,
    *,
    rounds: list[MockRound] | None = None,
    sims: list[FinalSimulation] | None = None,
    health: RevisionHealth = R_OK,
    recent: set[str] | None = None,
    previous: dict[date, str] | None = None,
) -> Readiness:
    sims = sims or []
    all_rounds = (m_ok_rounds() if rounds is None else rounds) + [r for s in sims for r in s.rounds]
    return calculate_readiness(
        components=world.components(),
        states=world.states,
        gap_report=world.gaps(),
        graph=graph(),
        profile=profile(),
        mock_rounds=all_rounds,
        final_simulations=sims,
        revision_health=health,
        recent_components={c.key for c in profile().components} if recent is None else recent,
        previous_states=previous or {},
        as_of_date=world.as_of,
    )
