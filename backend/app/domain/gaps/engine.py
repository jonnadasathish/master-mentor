"""Gap engine (GAP_ENGINE.md §2-§10): what is wrong, how badly, why, and what kind of work fixes it.

Pure and deterministic: all inputs are passed in; iteration follows seed / topological order; ties are broken
by explicit keys. No I/O, no clock.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from types import ModuleType

from app.domain.gaps.model import ACTIONABLE, BlockedBy, Gap, GapReport, RevisionFacts, SkillFacts
from app.domain.profile.model import Goal, ProfileSpec, SkillGraph, SkillSpec
from app.domain.readiness.components import ComponentScores
from app.domain.skills.state import SkillState, round_half_up

NO_FACTS = SkillFacts()
NO_REVISION = RevisionFacts()
STATUS_GROUP = {"NONE": 1, "BLOCKED": 2, "PARKED": 3}  # actionable statuses are group 0


def prep_phase(target_date: date | None, as_of: date, ruleset: ModuleType) -> tuple[str, Decimal | None]:
    """§2. ``weeks_left`` is exact (Decimal days / 7); display rounds it."""
    if target_date is None:
        return "BUILD", None
    weeks_left = Decimal((target_date - as_of).days) / Decimal(7)
    if weeks_left > ruleset.PHASE_BUILD_ABOVE_WEEKS:
        return "BUILD", weeks_left
    if weeks_left > ruleset.PHASE_SHARPEN_AT_OR_BELOW_WEEKS:
        return "CONSOLIDATE", weeks_left
    return "SHARPEN", weeks_left


def status_for(priority: int, ruleset: ModuleType) -> str:
    for status, minimum in ruleset.STATUS_THRESHOLDS:
        if priority >= minimum:
            return str(status)
    return "NONE"


@dataclass
class _Work:
    """Mutable per-skill working values while the report is assembled (never escapes this module)."""

    spec: SkillSpec
    state: SkillState
    facts: SkillFacts
    revision: RevisionFacts
    assessed: bool
    raw_gap: int | None = None
    severity: Decimal | None = None
    pressure_bp: int | None = None
    pressure_terms: tuple[str, ...] = ()
    priority: int = 0
    unsatisfied: tuple[BlockedBy, ...] = ()
    blocked: bool = False
    parked_reason: str | None = None
    status: str = "NONE"
    unlocks: tuple[tuple[int, str], ...] = ()  # (dependent priority, dependent key)


def _unassessed_state(key: str) -> SkillState:
    return SkillState(
        key, None, None, None, "NONE", None, None, 0, 0, None, None, "UNASSESSED", False, False, (), ()
    )


def _base(
    w: _Work, graph: SkillGraph, components: ComponentScores, profile: ProfileSpec, ruleset: ModuleType
) -> None:
    spec = w.spec
    if not w.assessed:
        downstream = len(graph.dependents.get(spec.key, ()))
        bonus = ruleset.ASSESS_DOWNSTREAM_BONUS * min(downstream, ruleset.ASSESS_DOWNSTREAM_MAX)
        w.priority = min(100, round_half_up(Decimal(spec.importance * (100 + bonus)) / Decimal(100)))
        return
    effective = w.state.effective_score or 0
    w.raw_gap = max(spec.target - effective, 0)
    w.severity = Decimal(w.raw_gap * spec.importance) / Decimal(100)
    terms: list[str] = []
    pressure = int(ruleset.PRESSURE_BASE_BP)
    if w.facts.n_fail_last5 >= ruleset.FAILURE_MIN_COUNT:
        pressure += ruleset.FAILURE_BP_PER_FAIL * min(w.facts.n_fail_last5, ruleset.FAILURE_MAX_COUNTED)
        terms.append("FAILURE")
    if w.facts.mock_weakness:
        pressure += ruleset.MOCK_BP
        terms.append("MOCK")
    if components.score(spec.component) < profile.component(spec.component).gate:
        pressure += ruleset.GATE_BP
        terms.append("GATE")
    if spec.floor > 0 and effective < spec.floor:
        pressure += ruleset.FLOOR_BP
        terms.append("FLOOR")
    days = w.facts.days_since_last_practice
    if (
        spec.importance >= ruleset.RETENTION_PRESSURE_MIN_IMPORTANCE
        and days is not None
        and days > (ruleset.RETENTION_PRESSURE_DAYS)
    ):
        pressure += ruleset.RETENTION_BP
        terms.append("RETENTION")
    w.pressure_bp = min(pressure, int(ruleset.PRESSURE_CAP_BP))
    w.pressure_terms = tuple(terms)
    w.priority = min(100, round_half_up(w.severity * w.pressure_bp / Decimal(10000)))


def _phase_parked(w: _Work, phase: str) -> bool:
    tier, level = w.spec.tier, w.state.level
    low = not w.assessed or (level is not None and level <= 1)
    if tier == "T1" or phase == "BUILD":
        return False
    if tier == "T4":
        return True
    if phase == "CONSOLIDATE":
        return tier == "T3" and low
    # SHARPEN
    if tier == "T3":
        return not w.assessed or (level is not None and level < 3)
    return tier == "T2" and low


def _feasibility(
    work: Mapping[str, _Work], profile: ProfileSpec, weeks_left: Decimal, ruleset: ModuleType
) -> tuple[tuple[str, ...], dict[str, tuple[int, int]]]:
    """§8. Returns infeasible components and, per component, (needed, available) minutes after parking."""
    infeasible: list[str] = []
    numbers: dict[str, tuple[int, int]] = {}
    for comp in profile.components:
        track_components = profile.track_components.get(comp.track, ())
        weight_sum = sum(c.weight for c in profile.components if c.key in track_components) or comp.weight
        track_share = Decimal(profile.track_minutes.get(comp.track, 0) * comp.weight) / Decimal(weight_sum)
        available = track_share * weeks_left
        per_point = int(ruleset.MIN_PER_POINT[comp.key])
        while _needed(work, comp.key, per_point) > available:
            parkable = [w for w in _feasibility_pool(work, comp.key) if w.spec.tier in ("T2", "T3")]
            if not parkable:
                infeasible.append(comp.key)
                break
            parkable.sort(
                key=lambda w: (
                    0 if w.spec.tier == "T3" else 1,
                    w.spec.importance,
                    -(w.raw_gap or 0),
                    w.spec.key,
                )
            )
            parkable[0].parked_reason = "NOT_FEASIBLE"
        numbers[comp.key] = (_needed(work, comp.key, per_point), int(available))  # display: floor
    return tuple(infeasible), numbers


def _feasibility_pool(work: Mapping[str, _Work], component: str) -> list[_Work]:
    """Unparked, assessed, required skills of a component (unassessed are excluded until measured)."""
    return [
        w
        for w in work.values()
        if w.spec.component == component and w.spec.required and w.assessed and w.parked_reason is None
    ]


def _needed(work: Mapping[str, _Work], component: str, per_point: int) -> int:
    return sum((w.raw_gap or 0) * per_point for w in _feasibility_pool(work, component))


def _gap_types(w: _Work, ruleset: ModuleType) -> list[tuple[str, str, str | None]]:
    """§6 decision table: all matching (type, stage, focus_skill) in table order."""
    s, f, spec = w.state, w.facts, w.spec
    level = s.level
    comm_skill = spec.key in ruleset.COMMUNICATION_SKILLS
    out: list[tuple[str, str, str | None]] = []
    if not w.assessed:
        out.append(("UNASSESSED", "DIAGNOSE", None))
    if w.status == "BLOCKED":
        focus = sorted(w.unsatisfied, key=lambda b: (b.score is not None, b.score or 0, b.skill))[0].skill
        out.append(("PREREQUISITE", "PREREQUISITE", focus))
    if not w.assessed or level is None:
        return out
    if not comm_skill and (
        level == 0
        or (
            level == 1
            and f.l1_rows >= ruleset.KNOWLEDGE_L1_ROWS
            and f.l1_recent_mean is not None
            and f.l1_recent_mean < ruleset.KNOWLEDGE_L1_BELOW_POINTS
        )
    ):
        out.append(("KNOWLEDGE", "LEARN" if level == 0 else "RECALL", None))
    peak_drop = (s.peak_score or 0) - (s.score or 0)
    days = f.days_since_last_practice
    if (
        peak_drop >= ruleset.RETENTION_PEAK_DROP and days is not None and days >= ruleset.RETENTION_MIN_DAYS
    ) or w.revision.max_active_lapses >= ruleset.RETENTION_MIN_LAPSES:
        out.append(("RETENTION", "REINFORCE", None))
    if spec.is_pattern and level >= 1 and f.pattern_misses_last4 >= ruleset.PATTERN_MIN_MISSES:
        out.append(("PATTERN_RECOGNITION", "PATTERN_DRILL", None))
    if level in (1, 2):
        out.append(("PRACTICE", "GUIDED" if level == 1 else "INDEPENDENT", None))
    if f.overconfident_rows >= ruleset.OVERCONFIDENT_MIN_COUNT:
        out.append(("CONFIDENCE", "RECALL" if level <= 1 else "INDEPENDENT", None))
    if level == 3 and (
        (f.speed_median_ratio_bp is not None and f.speed_median_ratio_bp > ruleset.SPEED_RATIO_BP)
        or f.timed_over_limit_last3 >= ruleset.SPEED_OVER_LIMIT_MIN_COUNT
    ):
        out.append(("SPEED", "TIMED", None))
    if level == 4 and f.depth_mean_last3 is not None and f.depth_mean_last3 < ruleset.DEPTH_BELOW_POINTS:
        out.append(("DEPTH", "EXPLAIN", None))
    comm_a = (
        f.communication_mean_last3 is not None
        and f.communication_mean_last3 < ruleset.COMMUNICATION_BELOW_POINTS
        and f.communication_outcome_mean_last3 is not None
        and f.communication_outcome_mean_last3 >= ruleset.COMMUNICATION_MIN_OUTCOME
    )
    comm_b = comm_skill and level <= 3 and f.scoring_rows >= ruleset.COMMUNICATION_SKILL_MIN_ROWS
    if comm_a or comm_b:
        out.append(("COMMUNICATION", "THINK_ALOUD", None))
    if (
        f.level_without_mocks is not None
        and f.level_without_mocks >= 4
        and f.latest_mock_points_60d is not None
        and f.latest_mock_points_60d < ruleset.INTERVIEW_EXECUTION_BELOW_POINTS
    ):
        out.append(("INTERVIEW_EXECUTION", "SIMULATE", None))
    if spec.component in ruleset.EXPERIENCE_COMPONENTS and level >= 4 and not f.has_l6_row:
        out.append(("EXPERIENCE", "TRANSFER", None))
    if not out and (w.raw_gap or 0) > 0:
        out.append(("LEVEL_UP", str(ruleset.LEVEL_UP_STAGE[level]), None))
    return out


def _reasons(w: _Work, types: list[str], ruleset: ModuleType) -> list[str]:
    s, f, spec = w.state, w.facts, w.spec
    effective = s.effective_score
    reasons: list[str] = []
    add = reasons.append
    if not w.assessed:
        add("UNASSESSED")
    if s.declared_unknown:
        add("DECLARED_UNKNOWN")
    if w.raw_gap is not None and w.raw_gap >= ruleset.LARGE_GAP_MIN:
        add("LARGE_GAP")
    if effective is not None and spec.floor > 0 and effective < spec.floor:
        add("BELOW_FLOOR")
    if spec.importance >= ruleset.HIGH_IMPORTANCE_MIN:
        add("HIGH_IMPORTANCE")
    if s.confidence == "LOW":
        add("LOW_CONFIDENCE")
    if "FAILURE" in w.pressure_terms or w.revision.has_leech:
        add("REPEATED_FAILURE")
    if "MOCK" in w.pressure_terms:
        add("MOCK_WEAKNESS")
    if "GATE" in w.pressure_terms:
        add("GATE_FAILING")
    if "RETENTION" in w.pressure_terms:
        add("RETENTION_RISK")
    if "RETENTION" in types:
        add("DECAYED")
    if "PATTERN_RECOGNITION" in types:
        add("PATTERN_MISIDENTIFIED")
    if "SPEED" in types:
        add("SPEED_BELOW_TARGET")
    if "CONFIDENCE" in types:
        add("OVERCONFIDENT")
    if f.underconfident_rows >= ruleset.UNDERCONFIDENT_MIN_COUNT:
        add("UNDERCONFIDENT")
    if f.studied_not_tested:
        add("STUDIED_NOT_TESTED")
    if w.status == "BLOCKED":
        add("PREREQUISITE_BLOCKED")
    for _, dependent in sorted(w.unlocks, key=lambda u: (-u[0], u[1]))[:3]:
        add(f"UNLOCKS:{dependent}")
    if w.parked_reason == "PARKED_DEADLINE":
        add("PARKED_DEADLINE")
    if w.parked_reason == "NOT_FEASIBLE":
        add("NOT_FEASIBLE")
    if w.revision.has_overdue_item:
        add("OVERDUE_REVISION")
    if effective is not None and effective >= spec.target and s.confidence == "HIGH":
        add("OVER_TARGET")
    return reasons


def calculate_gaps(
    *,
    skill_states: Mapping[str, SkillState],
    component_scores: ComponentScores,
    profile: ProfileSpec,
    graph: SkillGraph,
    skill_facts: Mapping[str, SkillFacts],
    revision_facts: Mapping[str, RevisionFacts],
    goal: Goal | None,
    as_of_date: date,
    ruleset: ModuleType,
) -> GapReport:
    phase, weeks_left = prep_phase(goal.target_date if goal else None, as_of_date, ruleset)
    work: dict[str, _Work] = {}
    for key, spec in graph.skills.items():
        state = skill_states.get(key) or _unassessed_state(key)
        w = _Work(
            spec=spec,
            state=state,
            facts=skill_facts.get(key, NO_FACTS),
            revision=revision_facts.get(key, NO_REVISION),
            assessed=state.assessed,
        )
        _base(w, graph, component_scores, profile, ruleset)
        work[key] = w

    # §7.2 prerequisite satisfaction (score, not effective).
    for w in work.values():
        unsatisfied = []
        for prereq, min_score in w.spec.prerequisites:
            p_score = work[prereq].state.score if prereq in work else None
            if p_score is None or p_score < min_score:
                unsatisfied.append(BlockedBy(prereq, p_score, min_score))
        w.unsatisfied = tuple(unsatisfied)
        w.blocked = bool(unsatisfied) and (not w.assessed or (w.state.level or 0) <= 2)

    # §8 parking: phase first, then feasibility.
    for w in work.values():
        if _phase_parked(w, phase):
            w.parked_reason = "PARKED_DEADLINE"
    required = [w for w in work.values() if w.spec.required]
    assessed_pct = 100 * sum(1 for w in required if w.assessed) // len(required) if required else 0
    feasibility_applied = (
        goal is not None
        and goal.target_date is not None
        and weeks_left is not None
        and assessed_pct >= ruleset.FEASIBILITY_MIN_ASSESSED_PCT
    )
    infeasible: tuple[str, ...] = ()
    feasibility: dict[str, tuple[int, int]] = {}
    if feasibility_applied and weeks_left is not None:
        infeasible, feasibility = _feasibility(work, profile, weeks_left, ruleset)

    # §7.1 status.
    for w in work.values():
        if w.parked_reason:
            w.status = "PARKED"
        elif w.blocked:
            w.status = "BLOCKED"
        elif not w.assessed:
            w.status = "UNASSESSED"
        else:
            w.status = status_for(w.priority, ruleset)

    # §7.2 unlock propagation, deepest first; parked skills do not propagate.
    share_num, share_den = ruleset.UNLOCK_SHARE
    for key in reversed(graph.topological_order):
        d = work.get(key)
        if d is None or d.status != "BLOCKED":
            continue
        for b in d.unsatisfied:
            p = work[b.skill]
            p.priority = max(p.priority, round_half_up(Decimal(d.priority * share_num) / Decimal(share_den)))
            p.unlocks = (*p.unlocks, (d.priority, d.spec.key))
    for w in work.values():
        if w.status not in ("PARKED", "BLOCKED", "UNASSESSED"):
            w.status = status_for(w.priority, ruleset)

    gaps: list[Gap] = []
    for w in work.values():
        matches = _gap_types(w, ruleset)
        types = [t for t, _, _ in matches]
        primary = matches[0] if matches else None
        f = w.facts
        evidence = {
            k: v
            for k, v in {
                "REPEATED_FAILURE": f.fail_refs if "FAILURE" in w.pressure_terms else (),
                "PATTERN_MISIDENTIFIED": f.pattern_refs if "PATTERN_RECOGNITION" in types else (),
                "SPEED_BELOW_TARGET": f.speed_refs if "SPEED" in types else (),
                "DEPTH": f.depth_refs if "DEPTH" in types else (),
                "COMMUNICATION": f.communication_refs if "COMMUNICATION" in types else (),
                "OVERCONFIDENT": f.confidence_refs if "CONFIDENCE" in types else (),
                "SKILL_STATE": tuple((r.source_type, r.source_id) for r in w.state.considered),
            }.items()
            if v
        }
        gaps.append(
            Gap(
                skill_key=w.spec.key,
                component=w.spec.component,
                tier=w.spec.tier,
                current_score=w.state.score,
                effective_score=w.state.effective_score,
                level=w.state.level,
                confidence=w.state.confidence,
                target_score=w.spec.target,
                floor_score=w.spec.floor,
                importance=w.spec.importance,
                raw_gap=w.raw_gap,
                severity=w.severity,
                pressure_bp=w.pressure_bp,
                priority=w.priority,
                status=w.status,
                rank=0,
                primary_gap_type=primary[0] if primary else None,
                gap_types=tuple(types),
                reason_codes=tuple(_reasons(w, types, ruleset)),
                blocked_by=w.unsatisfied if w.status == "BLOCKED" else (),
                parked_reason=w.parked_reason,
                focus_stage=primary[1] if primary else None,
                focus_skill=(primary[2] or w.spec.key) if primary else None,
                metrics={
                    "n_fail_last5": f.n_fail_last5,
                    "pattern_misses_last4": f.pattern_misses_last4,
                    "days_since_last_practice": f.days_since_last_practice,
                    "peak_score": w.state.peak_score,
                    "component_score": component_scores.score(w.spec.component),
                    "component_gate": profile.component(w.spec.component).gate,
                    "speed_median_ratio_bp": _plain(f.speed_median_ratio_bp),
                    "depth_mean_last3": _plain(f.depth_mean_last3),
                    "communication_mean_last3": _plain(f.communication_mean_last3),
                    "overconfident_rows": f.overconfident_rows,
                    "pressure_terms": list(w.pressure_terms),
                },
                evidence=evidence,
            )
        )

    gaps.sort(
        key=lambda g: (
            0 if g.status in ACTIONABLE else STATUS_GROUP[g.status],
            -g.priority,
            -g.importance,
            -1 if g.effective_score is None else g.effective_score,
            g.skill_key,
        )
    )
    ranked = tuple(replace(g, rank=i) for i, g in enumerate(gaps, start=1))
    return GapReport(
        as_of_date=as_of_date,
        phase=phase,
        weeks_left=weeks_left,
        infeasible_components=infeasible,
        feasibility_applied=feasibility_applied,
        gaps=ranked,
        feasibility=feasibility,
    )


def _plain(value: Decimal | None) -> str | None:
    return None if value is None else format(value.quantize(Decimal("0.01")), "f")
