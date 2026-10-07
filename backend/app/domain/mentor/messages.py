"""Mentor message rules (MENTOR_ENGINE.md §9): first match wins; every number in the text is in the payload."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from types import ModuleType
from typing import TYPE_CHECKING, Any

from app.domain.gaps.model import Gap
from app.domain.mentor.model import DailyPlan, Message, PlanInputs, PlanItem
from app.domain.mentor.roadmap import milestone_of
from app.domain.revision.engine import backlog_minutes, revision_cap

if TYPE_CHECKING:
    from app.domain.mentor.planner import Candidate

Rule = Callable[["_Ctx"], Message | None]


def _int(value: Decimal | None) -> int:
    return int((value or Decimal(0)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


class _Ctx:
    def __init__(
        self, plan: DailyPlan, inputs: PlanInputs, held: Sequence[Candidate], ruleset: ModuleType
    ) -> None:
        self.plan, self.inputs, self.held, self.ruleset = plan, inputs, held, ruleset
        self.gaps = inputs.gaps.by_skill()
        self.top_item: PlanItem | None = next((i for i in plan.items if i.candidate_type == "GAP"), None)
        self.top_gap: Gap | None = (
            self.gaps.get(self.top_item.skill) if self.top_item and self.top_item.skill else None
        )
        top_assessed = inputs.gaps.top_assessed(1)
        self.top_report_gap: Gap | None = top_assessed[0] if top_assessed else None
        self.planned_skills = [i.skill for i in plan.items if i.skill]

    def component_name(self, key: str) -> str:
        return next((c.name for c in self.inputs.profile.components if c.key == key), key)

    def reason_sentence(self, gap: Gap, codes: Sequence[str] | None = None) -> str:
        """§9 sentence of the first matching reason code (order fixed by the table)."""
        f = self.inputs.facts.get(gap.skill_key)
        codes = list(codes if codes is not None else gap.reason_codes)
        state = self.inputs.states.get(gap.skill_key)
        if "DECLARED_UNKNOWN" in codes:
            m = milestone_of(self.inputs.milestones).get(gap.skill_key)
            return f"Declared unknown, new topic in milestone {m.key if m else '-'}."
        if "DECAYED" in codes and f is not None and state is not None:
            return (
                f"Peak {state.peak_score}, now {state.score}; "
                f"last practiced {f.days_since_last_practice} days ago."
            )
        if "PATTERN_MISIDENTIFIED" in codes and f is not None:
            return f"{f.pattern_misses_last4} of your last 4 unseen {gap.skill_key} problems used the wrong approach"
        if "SPEED_BELOW_TARGET" in codes and f is not None:
            return f"median time is {_int((f.speed_median_ratio_bp or Decimal(0)) / 100)}% of target"
        if "REPEATED_FAILURE" in codes and f is not None:
            return f"{f.n_fail_last5} of your last 5 attempts failed"
        if "MOCK_WEAKNESS" in codes:
            return "flagged weak in a recent mock"
        if "BELOW_FLOOR" in codes:
            return f"effective {gap.effective_score} is below the floor {gap.floor_score}"
        if "PARKED_DEADLINE" in codes:
            return f"parked until after {self.inputs.target_date} ({self.inputs.phase})"
        if "NOT_FEASIBLE" in codes:
            return f"not feasible before {self.inputs.target_date} at the current pace"
        if "STUDIED_NOT_TESTED" in codes:
            return f"studied {self.inputs.practice.study_minutes_7d.get(gap.skill_key, 0)} min without a test"
        return f"{gap.raw_gap} points below target"


def _msg(rule: str, text: str, **payload: Any) -> Message:
    return Message(rule, text, payload)


def _end(sentence: str) -> str:
    return sentence if sentence.endswith(".") else sentence + "."


def r_calibration(c: _Ctx) -> Message | None:
    cal = c.inputs.calibration
    if not cal.calibration_mode or cal.hybrid:
        return None  # hybrid day: the learning mission's own message rule speaks (D-086)
    keys = [i.battery_item_key for i in c.plan.items if i.battery_item_key] or [
        i.candidate_key for i in c.plan.items if i.candidate_type == "DIAGNOSTIC"
    ]
    keys = [k for k in keys if k]
    # The diagnostics clause is only said when there is something to list (never "Today's diagnostics: .").
    diagnostics = f" Today's diagnostics: {', '.join(keys)}." if keys else ""
    return _msg(
        "CALIBRATION",
        f"Calibration: {cal.assessed_required}/{cal.required} required skills measured.{diagnostics} "
        "No new material until the baseline is complete.",
        assessed=cal.assessed_required,
        required=cal.required,
        items=keys,
    )


def r_infeasible(c: _Ctx) -> Message | None:
    comps = c.inputs.gaps.infeasible_components
    if not comps:
        return None
    comp = comps[0]
    needed, available = c.inputs.gaps.feasibility.get(comp, (0, 0))
    return _msg(
        "DEADLINE_INFEASIBLE",
        f"At the current pace {c.component_name(comp)} cannot reach target by {c.inputs.target_date} "
        f"(needs {needed} min, {available} available). Only critical skills are scheduled there; consider "
        "moving the date.",
        component=comp,
        needed=needed,
        available=available,
    )


def r_lapsed(c: _Ctx) -> Message | None:
    r = c.inputs.readiness
    if not r.lapsed or not r.blockers:
        return None
    b = r.blockers[0]
    return _msg(
        "READINESS_LAPSED",
        f"Readiness lapsed: {b.gate} failed ({b.actual} vs {b.required}). Restore it before anything else.",
        gate=b.gate,
        actual=b.actual,
        required=b.required,
    )


def r_backlog(c: _Ctx) -> Message | None:
    parked = {g.skill_key for g in c.inputs.gaps.gaps if g.status == "PARKED"}
    backlog = backlog_minutes(c.inputs.revision.items, parked, c.inputs.as_of, c.ruleset)
    cap = revision_cap(c.inputs.budget, c.ruleset)
    suspended = list(c.inputs.triage_suspended_today)
    if not suspended and backlog <= c.ruleset.TRIAGE_TRIGGER_MULTIPLE * cap:  # D-068
        return None
    return _msg(
        "BACKLOG_OVER_BUDGET",
        f"Revision backlog is {backlog} min, more than a day's budget. Revisions are limited to {cap} min/day "
        f"when other work exists; {len(suspended)} low-importance items were suspended.",
        backlog=backlog,
        cap=cap,
        suspended=suspended,
    )


def r_leech(c: _Ctx) -> Message | None:
    leech = {
        i.skill: i
        for i in c.inputs.revision.items.values()
        if i.state == "SUSPENDED" and i.suspend_reason == "LEECH"
    }
    for skill in c.planned_skills:
        if skill in leech:
            item = leech[skill]
            return _msg(
                "LEECH_RELEARN",
                f"You failed the {skill} revision {item.lapses} times. Stop re-reading; re-learn it with "
                "guided practice today.",
                item=item.item_key,
                lapses=item.lapses,
            )
    return None


def r_unlock(c: _Ctx) -> Message | None:
    g = c.top_gap
    if g is None:
        return None
    unlocks = [r.split(":", 1)[1] for r in g.reason_codes if r.startswith("UNLOCKS:")]
    if not unlocks:
        return None
    downstream = unlocks[0]
    spec = c.inputs.graph.skills[downstream]
    min_score = next((m for p, m in spec.prerequisites if p == g.skill_key), 0)
    return _msg(
        "PREREQUISITE_UNLOCK",
        f"Do not start {downstream} yet. {g.skill_key} ({g.current_score}/{min_score}) blocks it, so fix it first.",
        downstream=downstream,
        skill=g.skill_key,
        score=g.current_score,
        min_score=min_score,
    )


def r_new_topic_hold(c: _Ctx) -> Message | None:
    held = sorted((h for h in c.held if h.gap is not None), key=lambda h: h.gap.rank if h.gap else 0)
    if not held:
        return None
    first = held[0]
    blocker = c.gaps.get(first.held_detail or "")
    if blocker is None:
        return None
    return _msg(
        "NEW_TOPIC_HOLD",
        f"Do not start {first.skill} today. {blocker.skill_key} {blocker.primary_gap_type} is {blocker.status} "
        f"({blocker.priority}): {_end(c.reason_sentence(blocker))}",
        held_skill=first.skill,
        gap_skill=blocker.skill_key,
        gap_type=blocker.primary_gap_type,
        status=blocker.status,
        priority=blocker.priority,
    )


def r_timed(c: _Ctx) -> Message | None:
    g = c.top_gap
    if g is None or g.primary_gap_type != "SPEED":
        return None
    f = c.inputs.facts.get(g.skill_key)
    ratio = _int((f.speed_median_ratio_bp if f else Decimal(0)) or Decimal(0)) // 100
    return _msg(
        "SWITCH_TO_TIMED",
        f"You solve {g.skill_key} independently (L3), but median time is {ratio}% of target. Switch from "
        "learning to timed practice.",
        skill=g.skill_key,
        ratio=ratio,
    )


def r_pattern(c: _Ctx) -> Message | None:
    g = c.top_gap
    if g is None or g.primary_gap_type != "PATTERN_RECOGNITION":
        return None
    f = c.inputs.facts.get(g.skill_key)
    misses = f.pattern_misses_last4 if f else 0
    return _msg(
        "PATTERN_DRILL",
        f"In {misses} of your last 4 {g.skill_key} problems you chose the wrong approach. Drill recognition "
        "before solving more.",
        misses=misses,
    )


def r_communication(c: _Ctx) -> Message | None:
    g = c.top_gap
    if g is None or g.primary_gap_type != "COMMUNICATION":
        return None
    f = c.inputs.facts.get(g.skill_key)
    comm = _int(f.communication_mean_last3 if f else None)
    return _msg(
        "COMMUNICATION_GAP",
        f"Your solutions are correct, but your explanation scores average {comm}/100. Practice out loud, recorded.",
        comm=comm,
    )


def r_substep(c: _Ctx) -> Message | None:
    before = c.inputs.component_scores_28d_ago
    item = next(
        (
            i
            for i in c.plan.items
            if i.candidate_type == "GAP"
            and i.skill
            and c.inputs.graph.skills[i.skill].component == "system_design"
        ),
        None,
    )
    if item is None or item.skill is None or before is None or "system_design" not in before:
        return None
    sub = c.ruleset.SUBSTEP_DRILL
    f = c.inputs.facts.get(item.skill)
    low = sum(1 for p in (f.last3_points if f else ()) if p < sub["below_points"])
    delta = c.inputs.components.score("system_design") - before["system_design"]
    if low < sub["min_low_rows"] or delta < sub["min_delta"]:
        return None
    return _msg(
        "SUBSTEP_DRILL",
        f"Your system-design work is improving (+{delta}), but you keep failing {item.skill}. Drill {item.skill} "
        "instead of starting another system.",
        delta=delta,
        skill=item.skill,
    )


def r_overconfident(c: _Ctx) -> Message | None:
    for skill in c.planned_skills:
        g = c.gaps.get(skill)
        if g is not None and g.primary_gap_type == "CONFIDENCE":
            f = c.inputs.facts.get(skill)
            n = f.overconfident_rows if f else 0
            return _msg(
                "OVERCONFIDENT",
                f"You rated yourself ≥ 4 before {n} attempts on {skill} that you failed. Today is a closed-book check.",
                n=n,
                skill=skill,
            )
    return None


def r_underconfident(c: _Ctx) -> Message | None:
    for item in c.plan.items:
        g = c.gaps.get(item.skill) if item.skill else None
        if g is not None and "UNDERCONFIDENT" in g.reason_codes:
            f = c.inputs.facts.get(g.skill_key)
            ratings = list(f.underconfident_ratings) if f else []
            return _msg(
                "UNDERCONFIDENT",
                f"Your evidence on {g.skill_key} (L{g.level}, score {g.current_score}) is stronger than your "
                f"self-ratings ({', '.join(str(r) for r in ratings)}). Trust it and push to {item.stage}.",
                skill=g.skill_key,
                level=g.level,
                score=g.current_score,
                ratings=ratings,
                stage=item.stage,
            )
    return None


def r_mock_gap(c: _Ctx) -> Message | None:
    for skill in c.planned_skills:
        g = c.gaps.get(skill)
        if g is not None and g.primary_gap_type == "INTERVIEW_EXECUTION":
            f = c.inputs.facts.get(skill)
            mock = f.latest_mock_points_60d if f else None
            return _msg(
                "MOCK_GAP",
                f"{skill}: practice level L{g.level}, but your last mock scored {mock}. Practice under interview "
                "conditions.",
                skill=skill,
                level=g.level,
                mock=mock,
            )
    return None


def r_stop(c: _Ctx) -> Message | None:
    qualifying = sorted(
        (e for e in c.plan.stop_list if e.minutes_7d > 0), key=lambda e: (-e.minutes_7d, e.skill)
    )
    if not qualifying:
        return None
    e = qualifying[0]
    gap = c.gaps.get(e.skill)
    if e.code == "OVER_TARGET":
        reason = "above target; maintain only"
    elif gap is not None:
        reason = c.reason_sentence(gap, [e.code])  # D-068: the stop entry's own reason
    else:
        reason = e.code.lower()
    target = c.top_report_gap.skill_key if c.top_report_gap else "today's plan"
    return _msg(
        "STOP_STUDYING",
        f"Stop {e.skill}: {reason}. Move that time to {target}.",
        skill=e.skill,
        code=e.code,
        minutes_7d=e.minutes_7d,
        target=target,
    )


def r_studied(c: _Ctx) -> Message | None:
    e = next((x for x in c.plan.stop_list if x.code == "STUDIED_NOT_TESTED"), None)
    if e is None:
        return None
    minutes = c.inputs.practice.study_minutes_7d.get(e.skill, 0)
    return _msg(
        "STUDIED_NOT_TESTED",
        f"You studied {e.skill} {minutes} min without testing. Reading isn't evidence; take the recall check.",
        skill=e.skill,
        minutes=minutes,
    )


def r_sharpen(c: _Ctx) -> Message | None:
    if c.inputs.phase != "SHARPEN":
        return None
    weeks = int(c.inputs.weeks_left or 0) if (c.inputs.weeks_left or 0) > 0 else 0
    top = c.top_report_gap.skill_key if c.top_report_gap else "today's plan"
    return _msg(
        "SHARPEN_FOCUS",
        f"{weeks} weeks left. No new topics. Sharpen {top} and keep mocks going.",
        weeks_left=weeks,
        top_gap=top,
    )


def r_mock_due(c: _Ctx) -> Message | None:
    item = next((i for i in c.plan.items if i.candidate_type in ("MOCK", "FINAL_SIMULATION")), None)
    if item is None:
        return None
    label = item.round_type or "final simulation"
    return _msg(
        "MOCK_DUE", f"Mock day: {label}. Simulate interview conditions; score honestly.", round_type=label
    )


def r_blocker(c: _Ctx) -> Message | None:
    r = c.inputs.readiness
    if (
        r.state not in ("FOUNDATION", "DEVELOPING")
        or not r.blockers
        or c.top_item is None
        or c.top_gap is None
    ):
        return None
    b = r.blockers[0]
    skill_spec = c.inputs.graph.skills.get(b.skill) if b.skill else None
    component = b.component or (skill_spec.component if skill_spec else None)
    if component != c.top_gap.component:
        return None
    return _msg(
        "READINESS_BLOCKER",
        f"{r.state}: {b.message}. Today's work targets it: {c.top_gap.skill_key}.",
        state=r.state,
        gate=b.gate,
        blocker=b.message,
        skill=c.top_gap.skill_key,
    )


def r_ready(c: _Ctx) -> Message | None:
    if not c.inputs.readiness.at_least("INTERVIEW_READY"):
        return None
    return _msg(
        "READY_MAINTAIN",
        "Interview-ready. Maintain: revisions, a mock at least every 7 days, no new topics.",
        state=c.inputs.readiness.state,
    )


def r_default(c: _Ctx) -> Message:
    g = c.top_gap
    if g is None:
        return _msg("DEFAULT", "No gaps above threshold today. Revisions and maintenance only.")
    return _msg(
        "DEFAULT",
        f"Top priority: {g.skill_key} ({g.status}, {g.priority}): {g.primary_gap_type}. "
        f"{_end(c.reason_sentence(g))}",
        skill=g.skill_key,
        status=g.status,
        priority=g.priority,
        gap_type=g.primary_gap_type,
    )


RULES: dict[str, Rule] = {
    "CALIBRATION": r_calibration,
    "DEADLINE_INFEASIBLE": r_infeasible,
    "READINESS_LAPSED": r_lapsed,
    "BACKLOG_OVER_BUDGET": r_backlog,
    "LEECH_RELEARN": r_leech,
    "PREREQUISITE_UNLOCK": r_unlock,
    "NEW_TOPIC_HOLD": r_new_topic_hold,
    "SWITCH_TO_TIMED": r_timed,
    "PATTERN_DRILL": r_pattern,
    "COMMUNICATION_GAP": r_communication,
    "SUBSTEP_DRILL": r_substep,
    "OVERCONFIDENT": r_overconfident,
    "UNDERCONFIDENT": r_underconfident,
    "MOCK_GAP": r_mock_gap,
    "STOP_STUDYING": r_stop,
    "STUDIED_NOT_TESTED": r_studied,
    "SHARPEN_FOCUS": r_sharpen,
    "MOCK_DUE": r_mock_due,
    "READINESS_BLOCKER": r_blocker,
    "READY_MAINTAIN": r_ready,
}


def choose_message(
    plan: DailyPlan, inputs: PlanInputs, *, held_learn: Sequence[Candidate], ruleset: ModuleType
) -> Message:
    ctx = _Ctx(plan, inputs, held_learn, ruleset)
    for name in ruleset.MESSAGE_RULE_ORDER:
        if name == "DEFAULT":
            break
        message = RULES[name](ctx)
        if message is not None:
            return message
    return r_default(ctx)
