"""Daily plan generation (MENTOR_ENGINE.md §3-§8). Pure: ``generate_daily_plan(inputs, ruleset)``.

Candidates -> unified scores -> track floors -> deterministic sort -> one greedy pass under explicit
constraints -> focus follow-up -> stop list -> message (``messages.py``). Every rejection is reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from types import ModuleType

from app.domain.catalog.model import MissionTemplate
from app.domain.catalog.templates import resolve_template
from app.domain.gaps.model import Gap
from app.domain.mentor.messages import choose_message
from app.domain.mentor.model import DailyPlan, Dropped, Explanation, PlanInputs, PlanItem, StopEntry
from app.domain.mentor.picker import STAGE_DIFFICULTY, greedy_cover, pattern_drill_statements, pick_problem
from app.domain.mentor.roadmap import current_milestones, learn_allowed_by_roadmap
from app.domain.revision.engine import backlog_items, revision_cap
from app.domain.revision.model import RevisionItem

ACTIONABLE_ASSESSED = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
REVISION_TEMPLATE = {
    "PROBLEM": "revision.problem",
    "PATTERN": "revision.pattern",
    "CS": "revision.cs",
    "CONCEPT": "revision.concept",
    "SD": "revision.sd",
    "MOCK_WEAKNESS": "revision.mock_weakness",
}
BATTERY_ATTEMPT_PROBLEMS = 2  # "2 unseen MEDIUM problems" in every DSA battery item (D-069)
MOCK_REVIEW_MINUTES = 15  # mock.round minutes_rule: round minutes + 15 review
FOLLOW_UP_TERMINAL = ("GAP_ENGINE", "MOCK", None)


@dataclass
class Candidate:
    key: str
    type: str
    skill: str | None
    score: int
    minutes: int
    stage: str | None = None
    template: MissionTemplate | None = None
    due_date: date | None = None
    effective: int | None = None
    importance: int = 0
    last_practiced: date | None = None
    problem_ids: tuple[int, ...] = ()
    revision_item_key: str | None = None
    battery_item_key: str | None = None
    round_type: str | None = None
    reason_codes: tuple[str, ...] = ()
    gap: Gap | None = None
    is_learn: bool = False
    held: str | None = (
        None  # NEW_TOPIC_HOLD | HELD_BY_ROADMAP | NEW_TOPIC_LIMIT | CONTENT_MISSING | MIN_BUDGET
    )
    held_detail: str | None = None
    track: str | None = None
    carried_from: int | None = None
    order: int = 0  # battery order for BASELINE
    tags: set[str] = field(default_factory=set)


# ------------------------------------------------------------------------------------------- helpers


def _track_of(component: str, inputs: PlanInputs) -> str | None:
    comp = next((c for c in inputs.profile.components if c.key == component), None)
    return comp.track if comp else None


def _template_minutes(t: MissionTemplate | None, fallback: int = 0) -> int:
    return t.minutes if t is not None and t.minutes is not None else fallback


def _last_practiced(inputs: PlanInputs, skill: str | None) -> date | None:
    if skill is None:
        return None
    days = inputs.facts.get(skill)
    if days is None or days.days_since_last_practice is None:
        return None
    return inputs.as_of - timedelta(days=days.days_since_last_practice)


def _leech_skills(inputs: PlanInputs) -> dict[str, RevisionItem]:
    return {
        i.skill: i
        for i in inputs.revision.items.values()
        if i.state == "SUSPENDED" and i.suspend_reason == "LEECH"
    }


def step_down(stage: str, ruleset: ModuleType) -> str:
    stage = str(ruleset.SPECIAL_STAGE_STEP_DOWN.get(stage, stage))
    ladder = [str(s) for s in ruleset.STAGE_LADDER]
    if stage in ladder:
        return ladder[max(ladder.index(stage) - 1, 0)]
    return stage


def _too_hard_recently(inputs: PlanInputs, skill: str, ruleset: ModuleType) -> bool:
    recent = [
        h
        for h in inputs.plan_history
        if h.skill == skill
        and 0 < (inputs.as_of - h.plan_date).days <= ruleset.TOO_HARD_WINDOW_DAYS
        and h.status != "DISCARDED"
    ]
    recent.sort(key=lambda h: h.plan_date)
    return bool(recent) and recent[-1].status == "SKIPPED" and recent[-1].skip_reason == "TOO_HARD"


def _continuation(inputs: PlanInputs, skill: str, ruleset: ModuleType) -> bool:
    done = [
        h
        for h in inputs.plan_history
        if h.skill == skill and h.status == "DONE" and h.plan_date < inputs.as_of
    ]
    return (
        bool(done)
        and (inputs.as_of - max(h.plan_date for h in done)).days <= ruleset.CONTINUATION_WINDOW_DAYS
    )


def _resolve(
    inputs: PlanInputs, component: str, stage: str, skill: str, gap_type: str | None
) -> MissionTemplate | None:
    r = resolve_template(
        inputs.templates, component=component, stage=stage, skill_key=skill, gap_type=gap_type
    )
    return r.template if r else None


def _attach_content(c: Candidate, inputs: PlanInputs, used: set[int]) -> None:
    """Template min_budget and problems; sets ``held`` when content is missing."""
    t = c.template
    if t is None:
        c.held = "CONTENT_MISSING"
        return
    if t.min_budget is not None and t.min_budget > inputs.budget:
        c.held = "MIN_BUDGET"
        return
    if not t.needs_problem or c.skill is None or c.problem_ids:
        return
    spec = inputs.graph.skills.get(c.skill)
    tier = spec.tier if spec else "T2"
    if c.stage == "PATTERN_DRILL":
        picked = pattern_drill_statements(
            skill=c.skill, problems=inputs.problems, graph=inputs.graph, states=inputs.states, exclude=used
        )
        if picked is None:
            c.held, c.held_detail = "CONTENT_MISSING", f"add 3 problems for {c.skill}"
            return
        c.problem_ids = picked
        return
    if c.stage == "DIAGNOSE":
        unassessed = {k for k, s in inputs.states.items() if not s.assessed}
        diff = "EASY" if tier == "T3" else "MEDIUM"
        picked_cover = greedy_cover(
            target_skills={c.skill},
            unassessed=unassessed | {c.skill},
            problems=inputs.problems,
            difficulty=diff,
            count=1,
            exclude=used,
        )
        if not picked_cover:
            c.held, c.held_detail = "CONTENT_MISSING", f"add 3 problems for {c.skill}"
            return
        c.problem_ids = picked_cover
        return
    pid = pick_problem(
        stage=c.stage or "INDEPENDENT",
        skill=c.skill,
        tier=tier,
        problems=inputs.problems,
        as_of=inputs.as_of,
        exclude=used,
    )
    if pid is None:
        c.held, c.held_detail = "CONTENT_MISSING", f"add 3 problems for {c.skill}"
        return
    c.problem_ids = (pid,)


# ------------------------------------------------------------------------------------------- candidates


def _revision_candidates(inputs: PlanInputs, parked: set[str], ruleset: ModuleType) -> list[Candidate]:
    out: list[Candidate] = []
    extra = int(ruleset.REINFORCE_EXTRA_MINUTES)
    by_key = {t.key: t for t in inputs.templates}
    for item in inputs.revision.items.values():
        if item.skill in parked or item.due_date is None or item.due_date > inputs.as_of:
            continue
        spec = inputs.graph.skills.get(item.skill)
        importance = spec.importance if spec else 0
        if item.state == "ACTIVE":
            if item.due_date < inputs.as_of:
                overdue = min(item.days_overdue(inputs.as_of), ruleset.REVISION_SCORE_OVERDUE_MAX_DAYS)
                score = min(
                    ruleset.REVISION_SCORE_CAP,
                    ruleset.REVISION_SCORE_OVERDUE_BASE
                    + overdue
                    + importance // ruleset.REVISION_SCORE_IMPORTANCE_DIVISOR,
                )
            else:
                score = (
                    ruleset.REVISION_SCORE_DUE_BASE + importance // ruleset.REVISION_SCORE_IMPORTANCE_DIVISOR
                )
        elif item.state == "GRADUATED" and spec is not None and spec.tier in ("T1", "T2"):
            score = (
                ruleset.REVISION_SCORE_MAINTENANCE_BASE
                + importance // ruleset.REVISION_SCORE_IMPORTANCE_DIVISOR
            )
        else:
            continue
        if item.needs_reinforcement:
            template_key = "revision.reinforce"
        elif item.item_type == "BEHAVIORAL":
            template_key = "revision.story" if item.item_key.startswith("STORY:") else "revision.project"
        else:
            template_key = REVISION_TEMPLATE.get(item.item_type, "revision.concept")
        state = inputs.states.get(item.skill)
        out.append(
            Candidate(
                key=f"REV:{item.item_key}",
                type="REVISION",
                skill=item.skill,
                score=int(score),
                minutes=item.total_minutes(extra),
                stage="REINFORCE" if item.needs_reinforcement else "REVISION",
                template=by_key.get(template_key),
                due_date=item.due_date,
                effective=state.effective_score if state else None,
                importance=importance,
                last_practiced=_last_practiced(inputs, item.skill),
                problem_ids=(int(item.subject_ref),) if item.item_type == "PROBLEM" else (),
                revision_item_key=item.item_key,
                track=_track_of(spec.component, inputs) if spec else None,
                tags={"maintenance"} if item.state == "GRADUATED" else set(),
            )
        )
    return out


def _baseline_candidates(inputs: PlanInputs) -> list[Candidate]:
    out: list[Candidate] = []
    unassessed = {k for k, s in inputs.states.items() if not s.assessed} | {
        k for k in inputs.graph.skills if k not in inputs.states
    }
    used: set[int] = set()
    for order, item in enumerate(i for i in inputs.calibration.items if not i.complete):
        problems: tuple[int, ...] = ()
        if item.observation_kind == "ATTEMPT":
            groups = set(item.covers)
            targets = {k for k, s in inputs.graph.skills.items() if s.group in groups}
            problems = greedy_cover(
                target_skills=targets,
                unassessed=unassessed,
                problems=inputs.problems,
                difficulty="MEDIUM",
                count=BATTERY_ATTEMPT_PROBLEMS,
                exclude=used,
            )
            used.update(problems)
        out.append(
            Candidate(
                key=f"BASE:{item.key}",
                type="BASELINE",
                skill=None,
                score=0,
                minutes=item.minutes,
                stage="DIAGNOSE",
                battery_item_key=item.key,
                problem_ids=problems,
                order=order,
            )
        )
    return out


def _gap_candidates(inputs: PlanInputs, ruleset: ModuleType) -> list[Candidate]:
    out: list[Candidate] = []
    leech = _leech_skills(inputs)
    current = current_milestones(inputs.milestones, inputs.states, inputs.graph, inputs.exit_facts)
    hard_gaps = {
        _track_of(g.component, inputs): g
        for g in reversed(inputs.gaps.gaps)  # reversed: the best-ranked gap per track wins
        if g.status in ("CRITICAL", "HIGH") and (g.level or 0) >= 1 and g.effective_score is not None
    }
    for g in inputs.gaps.gaps:
        if g.status not in ACTIONABLE_ASSESSED or g.focus_stage is None:
            continue
        skill = g.skill_key
        stage = g.focus_stage
        if skill in leech:
            stage = "LEARN" if (g.level or 0) <= 1 else "GUIDED"
        if _too_hard_recently(inputs, skill, ruleset):
            stage = step_down(stage, ruleset)
        state = inputs.states.get(skill)
        track = _track_of(g.component, inputs)
        c = Candidate(
            key=f"GAP:{skill}",
            type="GAP",
            skill=skill,
            score=g.priority + (ruleset.CONTINUATION_BONUS if _continuation(inputs, skill, ruleset) else 0),
            minutes=0,
            stage=stage,
            effective=g.effective_score,
            importance=g.importance,
            last_practiced=_last_practiced(inputs, skill),
            reason_codes=g.reason_codes,
            gap=g,
            is_learn=stage == "LEARN",
            track=track,
        )
        if c.is_learn:
            spec = inputs.graph.skills[skill]
            hold = hard_gaps.get(track)
            if inputs.phase == "SHARPEN" or (inputs.phase == "CONSOLIDATE" and spec.tier not in ("T1", "T2")):
                c.held = "NEW_TOPIC_LIMIT"
            elif hold is not None and hold.skill_key != skill:
                c.held, c.held_detail = "NEW_TOPIC_HOLD", hold.skill_key
            elif not learn_allowed_by_roadmap(skill, inputs.milestones, current):
                c.held = "HELD_BY_ROADMAP"
        c.template = _resolve(inputs, g.component, stage, skill, g.primary_gap_type)
        c.minutes = _template_minutes(c.template)
        if state is not None and c.effective is None:
            c.effective = state.effective_score
        out.append(c)
    return out


def _diagnostic_candidates(inputs: PlanInputs) -> list[Candidate]:
    out: list[Candidate] = []
    for g in inputs.gaps.gaps:
        if g.status != "UNASSESSED":
            continue
        if inputs.phase == "SHARPEN" and g.tier not in ("T1", "T2"):
            continue
        factor_num, factor_den = (100, 100) if inputs.calibration.calibration_mode else (70, 100)
        t = _resolve(inputs, g.component, "DIAGNOSE", g.skill_key, "UNASSESSED")
        out.append(
            Candidate(
                key=f"DIAG:{g.skill_key}",
                type="DIAGNOSTIC",
                skill=g.skill_key,
                score=g.priority * factor_num // factor_den,
                minutes=_template_minutes(t),
                stage="DIAGNOSE",
                template=t,
                importance=g.importance,
                reason_codes=g.reason_codes,
                gap=g,
                track=_track_of(g.component, inputs),
            )
        )
    return out


def _maintenance_candidates(inputs: PlanInputs, parked: set[str], ruleset: ModuleType) -> list[Candidate]:
    due_skills = {
        i.skill
        for i in inputs.revision.items.values()
        if i.due_date is not None and i.due_date <= inputs.as_of
    }
    out: list[Candidate] = []
    for key, spec in inputs.graph.skills.items():
        state = inputs.states.get(key)
        facts = inputs.facts.get(key)
        if spec.tier not in ("T1", "T2") or key in parked or key in due_skills or state is None:
            continue
        if state.effective_score is None or state.effective_score < spec.target or state.confidence != "HIGH":
            continue
        days = facts.days_since_last_practice if facts else None
        if days is None or days < ruleset.MAINTENANCE_MIN_DAYS_SINCE_PRACTICE:
            continue
        stage = str(ruleset.LEVEL_UP_STAGE[state.level or 0])
        t = _resolve(inputs, spec.component, stage, key, "LEVEL_UP")
        out.append(
            Candidate(
                key=f"MAINT:{key}",
                type="MAINTENANCE",
                skill=key,
                score=int(ruleset.MAINTENANCE_SCORE),
                minutes=_template_minutes(t),
                stage=stage,
                template=t,
                effective=state.effective_score,
                importance=spec.importance,
                last_practiced=_last_practiced(inputs, key),
                track=_track_of(spec.component, inputs),
            )
        )
    return out


def _mock_candidates(inputs: PlanInputs, ruleset: ModuleType) -> list[Candidate]:
    out: list[Candidate] = []
    by_key = {t.key: t for t in inputs.templates}
    if inputs.readiness.simulation_eligible and inputs.budget >= ruleset.FINAL_SIM_MIN_BUDGET:
        t = by_key.get("mock.final_simulation")
        out.append(
            Candidate(
                "FINAL_SIM",
                "FINAL_SIMULATION",
                None,
                int(ruleset.FINAL_SIM_SCORE),
                _template_minutes(t, int(ruleset.FINAL_SIM_MIN_BUDGET)),
                "SIMULATE",
                t,
            )
        )
    eligible = inputs.readiness.at_least("DEVELOPING") or inputs.phase != "BUILD"
    spacing = ruleset.MOCK_SPACING_DAYS_SHARPEN if inputs.phase == "SHARPEN" else ruleset.MOCK_SPACING_DAYS
    last = max((r.occurred_on for r in inputs.mock_rounds), default=None)
    if eligible and (last is None or (inputs.as_of - last).days >= spacing):
        latest = {
            rt: max((r.occurred_on for r in inputs.mock_rounds if r.round_type == rt), default=date.min)
            for rt in inputs.profile.round_types
        }
        loop = list(inputs.profile.round_types)
        round_type = min(loop, key=lambda rt: (latest[rt], loop.index(rt))) if loop else "DSA"
        minutes = inputs.profile.round_minutes.get(round_type, 45) + MOCK_REVIEW_MINUTES
        t = by_key.get("mock.round")
        out.append(
            Candidate(
                f"MOCK:{round_type}",
                "MOCK",
                None,
                int(ruleset.MOCK_SCORE),
                minutes,
                "SIMULATE",
                t,
                round_type=round_type,
            )
        )
    return out


def _apply_track_floors(candidates: list[Candidate], inputs: PlanInputs, ruleset: ModuleType) -> None:
    for track, minutes in inputs.profile.track_minutes.items():
        if track == "mock":
            continue
        comps = inputs.profile.track_components.get(track, ())
        failing = any(
            inputs.components.score(c) < inputs.profile.component(c).gate
            for c in comps
            if c in inputs.components.components
        )
        done = inputs.practice.track_minutes_7d.get(track, 0)
        if not failing or done * 100 >= minutes * ruleset.TRACK_FLOOR_PCT:
            continue
        pool = [c for c in candidates if c.track == track and c.held is None]
        if pool:
            best = sorted(pool, key=_sort_key)[0]
            best.score += int(ruleset.TRACK_FLOOR_BONUS)
            best.tags.add("TRACK_FLOOR")


def _sort_key(c: Candidate) -> tuple[object, ...]:
    return (
        -c.score,
        c.due_date is None,
        c.due_date or date.max,
        c.effective is not None,
        c.effective if c.effective is not None else -1,
        -c.importance,
        c.last_practiced is not None,
        c.last_practiced or date.min,
        c.key,
    )


# ------------------------------------------------------------------------------------------- packing


@dataclass
class _Pack:
    budget: int
    allocated: int = 0
    items: list[Candidate] = field(default_factory=list)
    gap_skills: set[str] = field(default_factory=set)
    non_revision_skills: set[str] = field(default_factory=set)
    revision_skills: set[str] = field(default_factory=set)
    revision_minutes: int = 0
    diagnostic_count: int = 0
    diagnostic_minutes: int = 0
    learn_count: int = 0
    mock_count: int = 0
    used_problems: set[int] = field(default_factory=set)

    @property
    def remaining(self) -> int:
        return self.budget - self.allocated


def _reject_reason(
    c: Candidate, p: _Pack, inputs: PlanInputs, rest: list[Candidate], ruleset: ModuleType
) -> str | None:
    if c.held is not None:
        return c.held
    if c.is_learn and (p.learn_count >= ruleset.MAX_LEARN_ITEMS or inputs.phase == "SHARPEN"):
        return "NEW_TOPIC_LIMIT"
    if c.type == "GAP" and c.skill not in p.gap_skills and len(p.gap_skills) >= ruleset.FOCUS_LIMIT_SKILLS:
        return "FOCUS_LIMIT"
    if c.type == "GAP" and inputs.calibration.hybrid and c.skill not in p.gap_skills and p.gap_skills:
        return "FOCUS_LIMIT"  # hybrid day: one learning mission, so the battery keeps its place
    if c.skill is not None:
        if c.type == "REVISION" and c.skill in p.revision_skills:
            return "PER_SKILL_LIMIT"
        if c.type in ("GAP", "DIAGNOSTIC", "MAINTENANCE") and c.skill in p.non_revision_skills:
            return "PER_SKILL_LIMIT"
    if c.type == "REVISION":
        cap = revision_cap(inputs.budget, ruleset)
        if p.revision_minutes + c.minutes > cap:
            other_fits = any(
                o.type != "REVISION" and o.held is None and o.minutes <= p.remaining for o in rest
            )
            if other_fits:
                return "REVISION_CAP"
    if c.type == "DIAGNOSTIC":
        if inputs.calibration.calibration_mode:
            if (
                p.diagnostic_minutes + c.minutes
                > inputs.budget * ruleset.CALIBRATION_DIAGNOSTIC_BUDGET_PCT // 100
            ):
                return "DIAGNOSTIC_LIMIT"
        elif p.diagnostic_count >= ruleset.MAX_DIAGNOSTIC_ITEMS:
            return "DIAGNOSTIC_LIMIT"
    if c.type in ("MOCK", "FINAL_SIMULATION") and p.mock_count >= 1:
        return "ITEM_CAP"
    if len(p.items) >= ruleset.MAX_PLAN_ITEMS:
        return "ITEM_CAP"
    if c.minutes > p.remaining:
        return "BUDGET"
    return None


def _admit(c: Candidate, p: _Pack) -> None:
    p.items.append(c)
    p.allocated += c.minutes
    p.used_problems.update(c.problem_ids)
    if c.type == "GAP" and c.skill:
        p.gap_skills.add(c.skill)
    if c.type in ("GAP", "DIAGNOSTIC", "MAINTENANCE") and c.skill:
        p.non_revision_skills.add(c.skill)
    if c.type == "REVISION" and c.skill:
        p.revision_skills.add(c.skill)
        p.revision_minutes += c.minutes
    if c.type == "DIAGNOSTIC":
        p.diagnostic_count += 1
        p.diagnostic_minutes += c.minutes
    if c.is_learn:
        p.learn_count += 1
    if c.type in ("MOCK", "FINAL_SIMULATION"):
        p.mock_count += 1


def _explanation(c: Candidate, inputs: PlanInputs) -> Explanation:
    g = c.gap
    state = inputs.states.get(c.skill) if c.skill else None
    spec = inputs.graph.skills.get(c.skill) if c.skill else None
    if c.type == "REVISION":
        evidence = f"revision item {c.revision_item_key} due {c.due_date}"
        outcome = "closed-book PASS moves the item up the ladder"
    elif c.type == "BASELINE":
        evidence = f"baseline battery item {c.battery_item_key}"
        outcome = "measures the covered skills"
    elif c.type in ("MOCK", "FINAL_SIMULATION"):
        evidence = f"mock round {c.round_type or 'final simulation'}"
        outcome = "L7 evidence per skill"
    else:
        evidence = ", ".join(c.reason_codes[:3]) if c.reason_codes else "gap below target"
        target_level = c.template.output_level if c.template is not None else None
        outcome = f"{c.template.pass_rule if c.template else 'pass'} (L{target_level} evidence)"
    return Explanation(
        current=state.score if state else None,
        effective=state.effective_score if state else None,
        target=spec.target if spec else None,
        priority=g.priority if g else None,
        evidence=evidence,
        expected_outcome=outcome,
    )


def _follow_up(p: _Pack, inputs: PlanInputs, ruleset: ModuleType) -> Candidate | None:
    first = next((c for c in p.items if c.type == "GAP"), None)
    if first is None or first.template is None or first.skill is None:
        return None
    nxt = first.template.next_on_pass
    if (
        p.remaining < ruleset.FOCUS_FOLLOW_UP_MIN_MINUTES
        or nxt in FOLLOW_UP_TERMINAL
        or len(p.items) >= ruleset.MAX_PLAN_ITEMS
    ):
        return None
    spec = inputs.graph.skills[first.skill]
    t = _resolve(inputs, spec.component, str(nxt), first.skill, None)
    if t is None:
        return None
    c = Candidate(
        key=f"FOLLOW:{first.skill}",
        type="FOLLOW_UP",
        skill=first.skill,
        score=first.score,
        minutes=_template_minutes(t),
        stage=str(nxt),
        template=t,
        effective=first.effective,
        importance=first.importance,
        reason_codes=("FOCUS_FOLLOW_UP",),
        gap=first.gap,
    )
    _attach_content(c, inputs, p.used_problems)
    if c.held == "CONTENT_MISSING" and first.problem_ids and t.needs_problem and c.stage != "PATTERN_DRILL":
        c.held, c.problem_ids = None, first.problem_ids[:1]  # deepen the same problem (D-069)
    if c.held is not None or c.minutes > p.remaining or c.minutes == 0:
        return None
    return c


def _stop_list(inputs: PlanInputs, ruleset: ModuleType) -> list[StopEntry]:
    out: list[StopEntry] = []
    total = inputs.practice.total_minutes_14d
    for g in sorted(inputs.gaps.gaps, key=lambda x: x.skill_key):
        minutes_7d = inputs.practice.skill_minutes_7d.get(g.skill_key, 0)
        state = inputs.states.get(g.skill_key)
        if g.status == "PARKED":
            out.append(
                StopEntry(
                    g.skill_key,
                    g.parked_reason or "PARKED_DEADLINE",
                    f"Stop studying {g.skill_key} until after the target date.",
                    minutes_7d,
                )
            )
        elif (
            state is not None
            and state.effective_score is not None
            and state.effective_score >= g.target_score
            and state.confidence == "HIGH"
            and total > 0
            and inputs.practice.skill_minutes_14d.get(g.skill_key, 0) * 100
            > total * ruleset.OVER_TARGET_SHARE_PCT
        ):
            out.append(
                StopEntry(g.skill_key, "OVER_TARGET", "Maintain only; move time to the top gap.", minutes_7d)
            )
        elif "STUDIED_NOT_TESTED" in g.reason_codes:
            out.append(
                StopEntry(
                    g.skill_key,
                    "STUDIED_NOT_TESTED",
                    f"Stop reading {g.skill_key}; test yourself (RECALL).",
                    minutes_7d,
                )
            )
    return out


# ------------------------------------------------------------------------------------------- entry point


def generate_daily_plan(inputs: PlanInputs, ruleset: ModuleType) -> DailyPlan:
    parked = {g.skill_key for g in inputs.gaps.gaps if g.status == "PARKED"}
    calibrating = inputs.calibration.calibration_mode
    battery_open = not inputs.calibration.battery_complete
    hybrid = inputs.calibration.hybrid
    budget = max(inputs.budget - inputs.done_minutes, 0)

    candidates = _revision_candidates(inputs, parked, ruleset)
    if battery_open:
        if hybrid:  # enough measured: the gap engine's top gap is today's learning mission (D-086)
            candidates += _gap_candidates(inputs, ruleset)
        candidates += _baseline_candidates(inputs)
    else:
        candidates += _gap_candidates(inputs, ruleset)
        candidates += _diagnostic_candidates(inputs)
        candidates += _maintenance_candidates(inputs, parked, ruleset)
        candidates += _mock_candidates(inputs, ruleset)
    candidates = [c for c in candidates if c.key not in inputs.kept_keys]  # never re-plan kept work today
    # carried over: original score + 5, once
    by_key = {c.key: c for c in candidates}
    for carried in inputs.carried_over:
        if carried.already_carried:
            continue
        existing = by_key.get(carried.candidate_key)
        bonus = carried.score + int(ruleset.CARRY_OVER_BONUS)
        if existing is not None:
            existing.score = max(existing.score, bonus)
            existing.carried_from = carried.item_id
    for c in candidates:
        if c.type not in ("REVISION", "BASELINE", "MOCK", "FINAL_SIMULATION"):
            _attach_content(c, inputs, set(inputs.blocked_problem_ids))
    if not battery_open:
        _apply_track_floors(candidates, inputs, ruleset)

    if battery_open:  # revisions, battery order; hybrid: gap mission first
        revisions = sorted((c for c in candidates if c.type == "REVISION"), key=_sort_key)
        gaps = sorted((c for c in candidates if c.type == "GAP"), key=_sort_key)
        battery = sorted((c for c in candidates if c.type == "BASELINE"), key=lambda c: c.order)
        ordered = gaps + revisions + battery if hybrid else revisions + battery  # hybrid: learning first
    else:
        ordered = sorted(candidates, key=_sort_key)

    pack = _Pack(budget=budget)
    pack.non_revision_skills |= set(inputs.kept_skills)
    pack.used_problems |= set(inputs.blocked_problem_ids)
    dropped: list[Dropped] = []
    final = next((c for c in ordered if c.type == "FINAL_SIMULATION" and c.minutes <= budget), None)
    if final is not None:
        _admit(final, pack)
        dropped.extend(Dropped(c.key, "ITEM_CAP") for c in ordered if c is not final)
    else:
        for i, c in enumerate(ordered):
            if c.type == "FINAL_SIMULATION":
                dropped.append(Dropped(c.key, "BUDGET"))
                continue
            reason = _reject_reason(c, pack, inputs, ordered[i + 1 :], ruleset)
            if reason is None and c.minutes <= 0 and c.type != "BASELINE":
                reason = "CONTENT_MISSING"
            if reason is not None:
                dropped.append(Dropped(c.key, reason, c.held_detail))
                continue
            if c.problem_ids and set(c.problem_ids) & pack.used_problems and c.type != "REVISION":
                _attach_content(replace_problems(c), inputs, pack.used_problems)
                if c.held is not None:
                    dropped.append(Dropped(c.key, c.held, c.held_detail))
                    continue
            _admit(c, pack)
        follow = _follow_up(pack, inputs, ruleset)
        if follow is not None:
            _admit(follow, pack)

    items = tuple(
        PlanItem(
            position=inputs.kept_items + n,
            candidate_type=c.type,
            candidate_key=c.key,
            skill=c.skill,
            template_key=c.template.key if c.template else None,
            stage=c.stage,
            minutes=c.minutes,
            score=c.score,
            problem_ids=c.problem_ids,
            revision_item_key=c.revision_item_key,
            battery_item_key=c.battery_item_key,
            round_type=c.round_type,
            reason_codes=tuple(sorted(c.tags)) + tuple(c.reason_codes) if c.tags else tuple(c.reason_codes),
            explanation=_explanation(c, inputs),
            carried_over_from_id=c.carried_from,
        )
        for n, c in enumerate(pack.items, start=1)
    )
    stop = tuple(_stop_list(inputs, ruleset))
    plan_wo_message = DailyPlan(
        plan_date=inputs.as_of,
        budget_minutes=inputs.budget,
        allocated_minutes=pack.allocated + inputs.done_minutes,
        unallocated_minutes=pack.remaining,
        phase=inputs.phase,
        calibration_mode=calibrating,
        items=items,
        stop_list=stop,
        dropped=tuple(dropped),
        message=None,  # type: ignore[arg-type]
    )
    held = [c for c in candidates if c.held == "NEW_TOPIC_HOLD"]
    message = choose_message(plan_wo_message, inputs, held_learn=held, ruleset=ruleset)
    return replace(plan_wo_message, message=message)


def replace_problems(c: Candidate) -> Candidate:
    """Clear problems so content is re-picked without ones already used today."""
    c.problem_ids = ()
    return c


__all__ = ["Candidate", "STAGE_DIFFICULTY", "backlog_items", "generate_daily_plan", "step_down"]
