"""Readiness (READINESS_MODEL.md §4-§10). Pure. The state is a function of gates only; the weighted score is
display-only and appears in no gate.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.domain.evidence.model import EvidenceRow
from app.domain.gaps.model import GapReport
from app.domain.profile.model import ProfileSpec, SkillGraph
from app.domain.readiness.components import ComponentScores
from app.domain.revision.model import RevisionHealth
from app.domain.skills.state import SkillState

STATES = ("NOT_MEASURED", "FOUNDATION", "DEVELOPING", "INTERVIEW_READY", "STRONG")
SELF_ROUND_CAP = 80
G1_T1_MIN_LEVEL = 3
G8_MIN_POINTS = 60


@dataclass(frozen=True)
class MockRound:
    id: int
    mock_id: int
    occurred_on: date
    round_type: str
    source: str  # SELF | PEER | PLATFORM
    round_score: int
    order: int = 0  # tie-break inside a day (occurred_at order); higher = later

    @property
    def score(self) -> int:
        return min(self.round_score, SELF_ROUND_CAP) if self.source == "SELF" else self.round_score


@dataclass(frozen=True)
class FinalSimulation:
    mock_id: int
    occurred_on: date
    source: str
    rounds: tuple[MockRound, ...]
    span_days: int = 0  # days between the first and last round (valid only within one local day)


@dataclass(frozen=True)
class Condition:
    gate: str
    subject: str
    kind: str  # component | skill | global
    actual: object
    required: object
    deficit: int
    message: str
    skills: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    failing: int


@dataclass(frozen=True)
class Readiness:
    as_of_date: date
    state: str
    simulation_eligible: bool
    lapsed: bool
    weighted_score: int
    limiting_component: str | None
    components: tuple[dict[str, object], ...]
    gates: tuple[GateResult, ...]
    blockers: tuple[Condition, ...]
    all_failing: tuple[Condition, ...]
    extra: dict[str, object] = field(default_factory=dict)


# ------------------------------------------------------------------------------------------- inputs


def recent_passing_components(
    rows: Sequence[EvidenceRow], graph: SkillGraph, as_of: date, days: int
) -> set[str]:
    """G8: components with >= 1 scoring row >= 60 points observed within the last ``days`` days."""
    out: set[str] = set()
    for r in rows:
        spec = graph.skills.get(r.skill)
        if (
            spec is not None
            and r.is_scoring
            and (r.outcome_points or 0) >= G8_MIN_POINTS
            and 0 <= (as_of - r.observed_on).days <= days
        ):
            out.add(spec.component)
    return out


# ------------------------------------------------------------------------------------------- gates


def _name(profile: ProfileSpec, key: str) -> str:
    return next((c.name for c in profile.components if c.key == key), key)


def _worst_skills(component: str, graph: SkillGraph, states: Mapping[str, SkillState]) -> tuple[str, ...]:
    def deficit(key: str) -> int:
        spec = graph.skills[key]
        eff = states[key].effective_score if key in states and states[key].effective_score is not None else 0
        return spec.importance * max(spec.target - (eff or 0), 0)

    required = [k for k, s in graph.skills.items() if s.component == component and s.required]
    return tuple(sorted(required, key=lambda k: (-deficit(k), k))[:3])


def _component_condition(
    gate: str,
    comp: str,
    actual: int,
    required: int,
    label: str,
    profile: ProfileSpec,
    graph: SkillGraph,
    states: Mapping[str, SkillState],
) -> Condition:
    return Condition(
        gate,
        comp,
        "component",
        actual,
        required,
        required - actual,
        f"{_name(profile, comp)} {label}{actual}{'%' if label else ''} < {required}{'%' if label else ''}",
        _worst_skills(comp, graph, states),
    )


def _g6(rounds: Sequence[MockRound], params: Mapping[str, object], as_of: date) -> list[Condition]:
    window = int(str(params.get("G6_mock_window_days", 60)))
    recent = sorted(
        (r for r in rounds if 0 <= (as_of - r.occurred_on).days <= window),
        key=lambda r: (r.occurred_on, r.order, r.id),
        reverse=True,
    )
    mins: Mapping[str, int] = params.get("G6_min_rounds_per_type", {})  # type: ignore[assignment]
    out: list[Condition] = []
    for rt, needed in mins.items():
        count = sum(1 for r in recent if r.round_type == rt)
        if count < needed:
            out.append(
                Condition(
                    "G6",
                    rt,
                    "global",
                    count,
                    needed,
                    needed - count,
                    f"{rt} rounds in 60 days {count} < {needed}",
                )
            )
        non_self = sum(1 for r in recent if r.round_type == rt and r.source != "SELF")
        need_ns = int(str(params.get("G6_min_non_self_rounds_per_type", 1)))
        if non_self < need_ns:
            out.append(
                Condition(
                    "G6",
                    f"{rt}:non_self",
                    "global",
                    non_self,
                    need_ns,
                    need_ns - non_self,
                    f"{rt} non-SELF rounds {non_self} < {need_ns}",
                )
            )
        latest = next((r for r in recent if r.round_type == rt), None)
        latest_min = int(str(params.get("G6_latest_per_type_min", 65)))
        if latest is not None and latest.score < latest_min:
            out.append(
                Condition(
                    "G6",
                    f"{rt}:latest",
                    "global",
                    latest.score,
                    latest_min,
                    latest_min - latest.score,
                    f"{rt} latest round {latest.score} < {latest_min}",
                )
            )
    last_n = recent[: int(str(params.get("G6_last_n_rounds", 6)))]
    mean_min = int(str(params.get("G6_last_n_mean_min", 70)))
    if last_n:
        mean = int(
            (Decimal(sum(r.score for r in last_n)) / len(last_n)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )
        if mean < mean_min:
            out.append(
                Condition(
                    "G6",
                    "last_6_mean",
                    "global",
                    mean,
                    mean_min,
                    mean_min - mean,
                    f"last 6 rounds mean {mean} < {mean_min}",
                )
            )
    each_min = int(str(params.get("G6_last_3_each_min", 55)))
    for r in recent[:3]:
        if r.score < each_min:
            out.append(
                Condition(
                    "G6",
                    f"round:{r.id}",
                    "global",
                    r.score,
                    each_min,
                    each_min - r.score,
                    f"{r.round_type} round {r.occurred_on} {r.score} < {each_min}",
                )
            )
    return out


def is_valid_final_simulation(sim: FinalSimulation, final_cfg: Mapping[str, object]) -> bool:
    types = {r.round_type for r in sim.rounds}
    required = set(final_cfg.get("required_round_types", ()))  # type: ignore[call-overload]
    one_of = set(final_cfg.get("one_of_round_types", ()))  # type: ignore[call-overload]
    max_span = int(str(final_cfg.get("max_span_days", 1)))
    return required <= types and bool(types & one_of) and sim.span_days < max_span


def final_simulation_failure(sim: FinalSimulation, params: Mapping[str, object]) -> str | None:
    round_min = int(str(params.get("G9_round_min", 70)))
    mean_min = int(str(params.get("G9_mean_min", 75)))
    for r in sorted(sim.rounds, key=lambda r: (r.score, r.round_type)):
        if r.score < round_min:
            return f"{r.round_type} {r.score} < {round_min}"
    mean = Decimal(sum(r.score for r in sim.rounds)) / len(sim.rounds)
    if mean < mean_min:
        return f"mean {int(mean.quantize(Decimal(1), rounding=ROUND_HALF_UP))} < {mean_min}"
    return None


def _g9(sims: Sequence[FinalSimulation], profile: ProfileSpec, as_of: date) -> list[Condition]:
    params, cfg = profile.gate_parameters, profile.final_simulation
    count = int(str(params.get("G9_final_sim_count", 3)))
    window = int(str(params.get("G9_window_days", 30)))
    valid = sorted(
        (s for s in sims if s.occurred_on <= as_of and is_valid_final_simulation(s, cfg)),
        key=lambda s: (s.occurred_on, s.mock_id),
        reverse=True,
    )[:count]
    if len(valid) < count:
        return [
            Condition(
                "G9",
                "final_simulations",
                "global",
                len(valid),
                count,
                count - len(valid),
                f"{len(valid)} of {count} final simulations",
            )
        ]
    out: list[Condition] = []
    for s in valid:
        failure = final_simulation_failure(s, params)
        if failure:
            out.append(
                Condition(
                    "G9",
                    f"sim:{s.occurred_on}",
                    "global",
                    failure,
                    "pass",
                    1,
                    f"final simulation {s.occurred_on} failed: {failure}",
                )
            )
    oldest = valid[-1]
    if (as_of - oldest.occurred_on).days > window:
        out.append(
            Condition(
                "G9",
                "window",
                "global",
                (as_of - oldest.occurred_on).days,
                window,
                1,
                f"oldest final simulation {oldest.occurred_on} is older than {window} days",
            )
        )
    one_of = list(cfg.get("one_of_round_types", ()))  # type: ignore[call-overload]
    covered = {r.round_type for s in valid for r in s.rounds}
    missing = [t for t in one_of if t not in covered]
    if missing:
        out.append(
            Condition(
                "G9",
                "coverage",
                "global",
                ",".join(sorted(covered & set(one_of))),
                ",".join(one_of),
                1,
                f"final simulations missing {', '.join(missing)}",
            )
        )
    non_self = sum(1 for s in valid if s.source != "SELF")
    need = int(str(params.get("G9_min_non_self", 2)))
    if non_self < need:
        out.append(
            Condition(
                "G9",
                "non_self",
                "global",
                non_self,
                need,
                need - non_self,
                f"non-SELF final simulations {non_self} < {need}",
            )
        )
    return out


def calculate_readiness(
    *,
    components: ComponentScores,
    states: Mapping[str, SkillState],
    gap_report: GapReport,
    graph: SkillGraph,
    profile: ProfileSpec,
    mock_rounds: Sequence[MockRound],
    final_simulations: Sequence[FinalSimulation],
    revision_health: RevisionHealth,
    recent_components: Collection[str],
    previous_states: Mapping[date, str],
    as_of_date: date,
) -> Readiness:
    p = profile.gate_parameters
    conditions: dict[str, list[Condition]] = {f"G{i}": [] for i in range(10)}
    t1 = [k for k, s in graph.skills.items() if s.tier == "T1"]

    def state_of(key: str) -> SkillState | None:
        return states.get(key)

    g0_min = int(str(p.get("G0_measured_min_assessed_pct", 70)))
    g1_min = int(str(p.get("G1_foundation_min_component", 45)))
    g3_min = int(str(p.get("G3_coverage_min_medium_confidence_pct", 80)))
    g4_level = int(str(p.get("G4_critical_min_level", 4)))
    g8_days = int(str(p.get("G8_recency_days", 21)))
    for comp in profile.components:
        c = components.components[comp.key]
        if c.assessed_pct < g0_min:
            conditions["G0"].append(
                _component_condition(
                    "G0", comp.key, c.assessed_pct, g0_min, "assessed ", profile, graph, states
                )
            )
        if c.score < g1_min:
            conditions["G1"].append(
                _component_condition("G1", comp.key, c.score, g1_min, "", profile, graph, states)
            )
        if c.score < comp.gate:
            conditions["G2"].append(
                _component_condition("G2", comp.key, c.score, comp.gate, "", profile, graph, states)
            )
        if c.medium_conf_pct < g3_min:
            conditions["G3"].append(
                _component_condition(
                    "G3", comp.key, c.medium_conf_pct, g3_min, "medium confidence ", profile, graph, states
                )
            )
        if comp.key not in recent_components:
            conditions["G8"].append(
                Condition(
                    "G8",
                    comp.key,
                    "component",
                    0,
                    1,
                    1,
                    f"{_name(profile, comp.key)} no passing evidence in {g8_days} days",
                    _worst_skills(comp.key, graph, states),
                )
            )
    for key in t1:
        s = state_of(key)
        level = s.level if s is not None and s.level is not None else 0
        if level < G1_T1_MIN_LEVEL:
            conditions["G1"].append(
                Condition(
                    "G1",
                    key,
                    "skill",
                    level,
                    G1_T1_MIN_LEVEL,
                    G1_T1_MIN_LEVEL - level,
                    f"{key} level L{level} < L{G1_T1_MIN_LEVEL}",
                    (key,),
                )
            )
        floor = graph.skills[key].floor
        eff = s.effective_score if s is not None and s.effective_score is not None else 0
        parts, deficit = [], 0
        if eff < floor:
            parts.append(f"{key} effective {eff} < {floor}")
            deficit = max(deficit, floor - eff)
        if level < g4_level:
            parts.append(f"{key} level L{level} < L{g4_level}")
            deficit = max(deficit, g4_level - level)
        if parts:
            conditions["G4"].append(
                Condition("G4", key, "skill", eff, floor, deficit, " / ".join(parts), (key,))
            )
    for g in gap_report.gaps:
        if g.status == "CRITICAL":
            conditions["G5"].append(
                Condition(
                    "G5",
                    g.skill_key,
                    "skill",
                    g.priority,
                    59,
                    g.priority - 59,
                    f"{g.skill_key} CRITICAL",
                    (g.skill_key,),
                )
            )
    conditions["G6"] = _g6(mock_rounds, p, as_of_date)
    g7_over = int(str(p.get("G7_overdue_days_max", 7)))
    if revision_health.overdue_t1_t2_over_7d > 0:
        n = revision_health.overdue_t1_t2_over_7d
        conditions["G7"].append(
            Condition("G7", "overdue", "global", n, 0, n, f"overdue T1/T2 > {g7_over} days: {n}")
        )
    g7_reviews = int(str(p.get("G7_min_reviews_in_window", 10)))
    if revision_health.reviews_30d < g7_reviews:
        n = revision_health.reviews_30d
        conditions["G7"].append(
            Condition(
                "G7",
                "reviews",
                "global",
                n,
                g7_reviews,
                g7_reviews - n,
                f"reviews in 30 days {n} < {g7_reviews}",
            )
        )
    g7_rate = int(str(p.get("G7_pass_rate_min_pct", 70)))
    rate = revision_health.pass_rate_30d
    if rate is not None and rate < g7_rate:
        conditions["G7"].append(
            Condition(
                "G7",
                "pass_rate",
                "global",
                rate,
                g7_rate,
                g7_rate - rate,
                f"review pass rate {rate}% < {g7_rate}%",
            )
        )
    conditions["G9"] = _g9(final_simulations, profile, as_of_date)

    def order(c: Condition) -> tuple[object, ...]:
        return (0 if c.kind == "component" else 1, -c.deficit, c.subject)

    for gate in conditions:
        conditions[gate].sort(key=order)
    passed = {gate: not conds for gate, conds in conditions.items()}
    if not passed["G0"]:
        state, next_gates = "NOT_MEASURED", ["G0"]
    elif not passed["G1"]:
        state, next_gates = "FOUNDATION", ["G1"]
    elif not all(passed[f"G{i}"] for i in range(2, 10)):
        state, next_gates = "DEVELOPING", [f"G{i}" for i in range(2, 10)]
    else:
        state, next_gates = "INTERVIEW_READY", []
    if state == "INTERVIEW_READY":
        stretch_ok = all(components.components[c.key].score >= c.stretch for c in profile.components)
        last6 = sorted(mock_rounds, key=lambda r: (r.occurred_on, r.order, r.id), reverse=True)[:6]
        strong_mean = int(str(p.get("STRONG_last_n_rounds_mean_min", 80)))
        mean_ok = bool(last6) and Decimal(sum(r.score for r in last6)) / len(last6) >= strong_mean
        days = int(str(p.get("STRONG_sustained_days", 14)))
        window = [as_of_date - timedelta(days=d) for d in range(1, days + 1)]
        sustained = all(previous_states.get(d) in ("INTERVIEW_READY", "STRONG") for d in window)
        if stretch_ok and mean_ok and sustained:
            state = "STRONG"
    simulation_eligible = all(passed[f"G{i}"] for i in range(9))
    lapsed = STATES.index(state) < STATES.index("INTERVIEW_READY") and any(
        s in ("INTERVIEW_READY", "STRONG")
        for d, s in previous_states.items()
        if 0 < (as_of_date - d).days <= 30
    )
    comps = tuple(
        {
            "key": c.key,
            "name": c.name,
            "score": components.components[c.key].score,
            "gate": c.gate,
            "stretch": c.stretch,
            "weight": c.weight,
            "assessed_pct": components.components[c.key].assessed_pct,
            "medium_conf_pct": components.components[c.key].medium_conf_pct,
            "passes_gate": components.components[c.key].score >= c.gate,
        }
        for c in profile.components
    )
    all_failing = tuple(c for gate in conditions for c in conditions[gate])
    return Readiness(
        as_of_date=as_of_date,
        state=state,
        simulation_eligible=simulation_eligible,
        lapsed=lapsed,
        weighted_score=components.weighted_score,
        limiting_component=components.limiting_component,
        components=comps,
        gates=tuple(GateResult(g, passed[g], len(conditions[g])) for g in conditions),
        blockers=tuple(c for g in next_gates for c in conditions[g]),
        all_failing=all_failing,
    )
