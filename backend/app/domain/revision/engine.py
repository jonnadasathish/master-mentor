"""Revision engine (REVISION_ENGINE.md §2-§9). Pure.

``project_revision_items`` replays, in time order, creation triggers and linked reviews (observations) and the
recorded actions. It never invents actions: triage and auto-resume only *propose* actions
(``triage_backlog``), which the plan-generating run records; a rebuild replays them.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from types import ModuleType

from app.domain.profile.model import SkillGraph, SkillSpec
from app.domain.revision.model import (
    ProposedAction,
    Review,
    RevisionAction,
    RevisionHealth,
    RevisionItem,
    RevisionObservation,
    RevisionProjection,
    RowFact,
)

NOT_REVISED_PREFIXES = ("execution.", "behavioral.", "communication.", "project.")
NOT_REVISED_SKILLS = ("dsa.pattern_recognition", "lld.machine_coding")
CONCEPT_PREFIXES = ("python.", "lld.", "engineering.", "testing.")


# ------------------------------------------------------------------------------------------- helpers


def skill_item_type(spec: SkillSpec) -> str | None:
    """§2: which item type (if any) revises a skill directly. Problems and stories are separate."""
    key = spec.key
    if key in NOT_REVISED_SKILLS or key.startswith(NOT_REVISED_PREFIXES):
        return None
    if spec.component == "cs":
        return "CS"
    if spec.component == "system_design":
        return "SD"
    if spec.component == "dsa":
        return "PATTERN" if spec.is_pattern else "CONCEPT"
    if key.startswith(CONCEPT_PREFIXES):
        return "CONCEPT"
    return None


def intervals(ladder: str, ruleset: ModuleType) -> tuple[int, ...]:
    return tuple(ruleset.MOCKW_INTERVALS if ladder == "MOCKW" else ruleset.STANDARD_INTERVALS)


def initial_index(points: int, time_ratio_bp: int | None, ruleset: ModuleType) -> int:
    """§3 initial index by the triggering row's outcome points (slow >= 90 counts as 50-89)."""
    table = ruleset.INITIAL_INDEX
    if points < 50:
        return int(table["below_50"])
    slow = time_ratio_bp is not None and time_ratio_bp > ruleset.INITIAL_INDEX_SLOW_RATIO_BP
    if points < 90 or slow:
        return int(table["50_to_89_or_slow"])
    return int(table["90_plus"])


def review_outcome(item: RevisionItem, obs: RevisionObservation, ruleset: ModuleType) -> str | None:
    """§5: PASS / PARTIAL / FAIL from the linked observation; None when it carries no measure for the item."""
    if item.item_type == "PROBLEM":
        if obs.outcome is None:
            return None
        if obs.outcome == "FAIL" or obs.solution_viewed:
            return "FAIL"
        within = obs.time_seconds is None or obs.time_seconds <= item.minutes * 60
        if obs.outcome == "PASS" and obs.hints_used == 0 and within:
            return "PASS"
        return "PARTIAL"
    row = next((r for r in obs.rows if r.skill == item.skill and r.is_scoring), None)
    if row is None or row.outcome_points is None:
        return None
    if row.outcome_points >= ruleset.REVIEW_PASS_MIN_POINTS:
        return "PASS"
    if row.outcome_points >= ruleset.REVIEW_PARTIAL_MIN_POINTS:
        return "PARTIAL"
    return "FAIL"


def _maintained(spec: SkillSpec | None) -> bool:
    return spec is not None and spec.tier in ("T1", "T2")


def schedule_revision(
    item: RevisionItem,
    outcome: str,
    review_date: date,
    spec: SkillSpec | None,
    ruleset: ModuleType,
) -> RevisionItem:
    """§5-§7 pure transition for one review."""
    if item.state == "GRADUATED":  # maintenance check (T1/T2 only)
        if outcome == "PASS":
            due = review_date + timedelta(days=ruleset.MAINTENANCE_DAYS)
            return replace(item, due_date=due, last_reviewed_on=review_date)
        if outcome == "PARTIAL":
            due = review_date + timedelta(days=ruleset.MAINTENANCE_PARTIAL_DAYS)
            return replace(item, due_date=due, last_reviewed_on=review_date)
        return replace(
            item,
            state="ACTIVE",
            interval_index=int(ruleset.MAINTENANCE_FAIL_INDEX),
            lapses=item.lapses + 1,
            due_date=review_date + timedelta(days=ruleset.MAINTENANCE_FAIL_DUE_DAYS),
            last_reviewed_on=review_date,
        )
    ladder = intervals(item.ladder, ruleset)
    if outcome == "PASS":
        if item.interval_index >= len(ladder) - 1:
            check: date | None = (
                review_date + timedelta(days=ruleset.MAINTENANCE_DAYS) if _maintained(spec) else None
            )
            return replace(
                item,
                state="GRADUATED",
                due_date=check,
                needs_reinforcement=False,
                last_reviewed_on=review_date,
            )
        index = item.interval_index + 1
        return replace(
            item,
            interval_index=index,
            due_date=review_date + timedelta(days=ladder[index]),
            needs_reinforcement=False,
            last_reviewed_on=review_date,
        )
    if outcome == "PARTIAL":
        return replace(
            item,
            due_date=review_date + timedelta(days=ladder[item.interval_index]),
            last_reviewed_on=review_date,
        )
    lapses = item.lapses + 1
    failed = replace(
        item,
        lapses=lapses,
        interval_index=0,
        needs_reinforcement=True,
        due_date=review_date + timedelta(days=ladder[0]),
        last_reviewed_on=review_date,
    )
    if lapses >= ruleset.LEECH_LAPSES:
        return replace(failed, state="SUSPENDED", suspend_reason="LEECH", suspended_on=review_date)
    return failed


def _new_item(
    *,
    key: str,
    item_type: str,
    skill: str,
    subject: str,
    index: int,
    on: date,
    minutes: int,
    ruleset: ModuleType,
    ladder: str = "STANDARD",
) -> RevisionItem:
    days = intervals(ladder, ruleset)[index]
    return RevisionItem(
        item_key=key,
        item_type=item_type,
        skill=skill,
        subject_ref=subject,
        ladder=ladder,
        state="ACTIVE",
        suspend_reason=None,
        interval_index=index,
        due_date=on + timedelta(days=days),
        lapses=0,
        needs_reinforcement=index == 0,
        created_on=on,
        last_reviewed_on=None,
        minutes=minutes,
    )


def _problem_item(obs: RevisionObservation, ruleset: ModuleType) -> RevisionItem | None:
    p = obs.problem
    if p is None or not p.is_catalog or p.primary_skill is None or obs.outcome is None:
        return None
    row = next((r for r in obs.rows if r.skill == p.primary_skill), None)
    ratio = row.time_ratio_bp if row else None
    slow = ratio is not None and ratio > ruleset.INITIAL_INDEX_SLOW_RATIO_BP
    if not (
        p.is_canonical
        or obs.outcome in ("FAIL", "PARTIAL")
        or obs.hints_used >= 1
        or obs.solution_viewed
        or slow
    ):
        return None  # a clean, fast, independent pass on a non-canonical problem: the pattern item covers it
    points = row.outcome_points if row and row.outcome_points is not None else 0
    return _new_item(
        key=f"PROBLEM:{p.id}",
        item_type="PROBLEM",
        skill=p.primary_skill,
        subject=str(p.id),
        index=initial_index(points, ratio, ruleset),
        on=obs.observed_on,
        minutes=int(ruleset.REVISION_ITEM_MINUTES[f"PROBLEM_{p.difficulty}"]),
        ruleset=ruleset,
    )


def _skill_items(
    obs: RevisionObservation, graph: SkillGraph, existing: Collection[str], ruleset: ModuleType
) -> list[RevisionItem]:
    out: list[RevisionItem] = []
    for r in obs.rows:
        spec = graph.skills.get(r.skill)
        if spec is None or not r.is_scoring or r.outcome_points is None:
            continue
        item_type = skill_item_type(spec)
        if item_type is None:
            continue
        key = f"{item_type}:{r.skill}"
        if key in existing:
            continue
        if item_type == "PATTERN":
            if r.level < 1:
                continue
            index = int(ruleset.INITIAL_INDEX["PATTERN"])
        else:
            if r.level < 2:
                continue
            index = initial_index(r.outcome_points, r.time_ratio_bp, ruleset)
        out.append(
            _new_item(
                key=key,
                item_type=item_type,
                skill=r.skill,
                subject=r.skill,
                index=index,
                on=obs.observed_on,
                minutes=int(ruleset.REVISION_ITEM_MINUTES[item_type]),
                ruleset=ruleset,
            )
        )
    return out


def _project_item(obs: RevisionObservation, ruleset: ModuleType) -> RevisionItem | None:
    if obs.kind != "PROJECT_WALKTHROUGH" or not obs.source_key or not obs.source_key.startswith("project:"):
        return None
    project = obs.source_key.split(":", 1)[1]
    item = _new_item(
        key=f"PROJECT:{project}",
        item_type="BEHAVIORAL",
        skill="project.architecture_walkthrough",
        subject=project,
        index=int(ruleset.INITIAL_INDEX["BEHAVIORAL"]),
        on=obs.observed_on,
        minutes=int(ruleset.REVISION_ITEM_MINUTES["PROJECT"]),
        ruleset=ruleset,
    )
    return replace(
        item, needs_reinforcement=False
    )  # reinforcement follows a < 50 row, not a new item (D-073)


@dataclass(frozen=True)
class WeaknessRound:
    """A saved mock round with its flagged skills: (skill, outcome_points)."""

    round_id: int
    occurred_on: date
    weaknesses: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class StoryFact:
    story_id: int
    created_on: date
    first_competency: str | None


def mock_weakness_items(rounds: Sequence[WeaknessRound], ruleset: ModuleType) -> list[RevisionItem]:
    """§2/§3: MOCKW:<round>:<skill>, max 3 per round (lowest outcome, then key), MOCKW ladder index 0."""
    items: list[RevisionItem] = []
    for r in rounds:
        for skill, _ in sorted(r.weaknesses, key=lambda w: (w[1], w[0]))[: ruleset.MOCKW_MAX_PER_ROUND]:
            base = _new_item(
                key=f"MOCKW:{r.round_id}:{skill}",
                item_type="MOCK_WEAKNESS",
                skill=skill,
                subject=f"{r.round_id}",
                index=0,
                on=r.occurred_on,
                minutes=int(ruleset.REVISION_ITEM_MINUTES["MOCK_WEAKNESS"]),
                ruleset=ruleset,
                ladder="MOCKW",
            )
            items.append(replace(base, needs_reinforcement=False))
    return items


def story_items(stories: Sequence[StoryFact], ruleset: ModuleType) -> list[RevisionItem]:
    """§2/§3: STORY:<id> created with the story; owned by its first competency; index 0."""
    out: list[RevisionItem] = []
    for s in stories:
        if s.first_competency is None:
            continue
        base = _new_item(
            key=f"STORY:{s.story_id}",
            item_type="BEHAVIORAL",
            skill=s.first_competency,
            subject=str(s.story_id),
            index=int(ruleset.INITIAL_INDEX["BEHAVIORAL"]),
            on=s.created_on,
            minutes=int(ruleset.REVISION_ITEM_MINUTES["STORY"]),
            ruleset=ruleset,
        )
        out.append(replace(base, needs_reinforcement=False))
    return out


# ------------------------------------------------------------------------------------------- projection


def project_revision_items(
    *,
    observations: Sequence[RevisionObservation],
    actions: Sequence[RevisionAction],
    graph: SkillGraph,
    as_of_date: date,
    ruleset: ModuleType,
    extra_items: Sequence[RevisionItem] = (),
) -> RevisionProjection:
    """Replay every event up to ``as_of_date`` (inclusive) in time order. ``extra_items`` seeds items created
    outside observations (stories, mock weaknesses) before replay."""
    events: list[tuple[date, datetime, int, int, object]] = []
    for o in observations:
        if o.observed_on <= as_of_date:
            events.append((o.observed_on, o.observed_at, 0, o.source_id, o))
    for a in actions:
        if a.action_on <= as_of_date:
            events.append((a.action_on, a.created_at, 1, a.id, a))
    events.sort(key=lambda e: (e[0], e[1], e[2], e[3]))

    items: dict[str, RevisionItem] = {i.item_key: i for i in extra_items if i.created_on <= as_of_date}
    reviews: list[Review] = []
    for on, at, _, _, event in events:
        if isinstance(event, RevisionAction):
            items = _apply_action(items, event, at)
            continue
        assert isinstance(event, RevisionObservation)
        obs = event
        # 1. review of a linked item
        if obs.revision_item_key and obs.revision_item_key in items:
            item = items[obs.revision_item_key]
            outcome = review_outcome(item, obs, ruleset)
            reviewable = item.state == "ACTIVE" or (item.state == "GRADUATED" and item.due_date is not None)
            if outcome is not None and reviewable:
                spec = graph.skills.get(item.skill)
                updated = schedule_revision(item, outcome, on, spec, ruleset)
                if updated.state == "SUSPENDED":
                    updated = replace(updated, suspended_at=at)
                items[item.item_key] = updated
                reviews.append(
                    Review(
                        item.item_key,
                        item.skill,
                        on,
                        outcome,
                        item.state == "GRADUATED",
                        obs.source_type,
                        obs.source_id,
                    )
                )
        # 2. creation triggers (first time only)
        created: list[RevisionItem] = []
        if obs.source_type == "ATTEMPT":
            problem_item = _problem_item(obs, ruleset)
            if problem_item is not None:
                created.append(problem_item)
        project_item = _project_item(obs, ruleset)
        if project_item is not None:
            created.append(project_item)
        created.extend(_skill_items(obs, graph, items, ruleset))
        for item in created:
            items.setdefault(item.item_key, item)
        # 3. leech reactivation by a strong later row on the skill
        for r in obs.rows:
            if not r.is_scoring or r.level < ruleset.REACTIVATION_MIN_LEVEL:
                continue
            if (r.outcome_points or 0) < ruleset.REACTIVATION_MIN_POINTS:
                continue
            for key, item in list(items.items()):
                if (
                    item.skill == r.skill
                    and item.state == "SUSPENDED"
                    and item.suspend_reason == "LEECH"
                    and item.suspended_at is not None
                    and at > item.suspended_at
                ):
                    items[key] = replace(
                        item,
                        state="ACTIVE",
                        suspend_reason=None,
                        interval_index=0,
                        lapses=1,
                        due_date=on + timedelta(days=1),
                        suspended_on=None,
                        suspended_at=None,
                    )
    return RevisionProjection(dict(sorted(items.items())), tuple(reviews))


def _apply_action(items: dict[str, RevisionItem], a: RevisionAction, at: datetime) -> dict[str, RevisionItem]:
    item = items.get(a.item_key)
    if item is None:
        return items
    if a.action == "SUSPEND" and item.state == "ACTIVE":
        items[a.item_key] = replace(
            item,
            state="SUSPENDED",
            suspend_reason=a.reason,
            suspended_on=a.action_on,
            suspended_at=at,
            due_before_suspension=item.due_date,
        )
    elif a.action == "RESUME" and item.state == "SUSPENDED":
        items[a.item_key] = replace(
            item,
            state="ACTIVE",
            suspend_reason=None,
            due_date=a.action_on,
            suspended_on=None,
            suspended_at=None,
        )
    return items


# ------------------------------------------------------------------------------------------- consumers


def revision_cap(daily_budget: int, ruleset: ModuleType) -> int:
    return max(int(ruleset.REVISION_CAP_MIN_MINUTES), daily_budget * int(ruleset.REVISION_CAP_PCT) // 100)


def backlog_items(
    items: Mapping[str, RevisionItem], parked: Collection[str], as_of: date
) -> list[RevisionItem]:
    """ACTIVE items due on or before ``as_of`` whose skill is not parked (maintenance checks excluded)."""
    return [i for i in items.values() if i.state == "ACTIVE" and i.is_due(as_of) and i.skill not in parked]


def backlog_minutes(
    items: Mapping[str, RevisionItem], parked: Collection[str], as_of: date, ruleset: ModuleType
) -> int:
    extra = int(ruleset.REINFORCE_EXTRA_MINUTES)
    return sum(i.total_minutes(extra) for i in backlog_items(items, parked, as_of))


def triage_backlog(
    *,
    items: Mapping[str, RevisionItem],
    graph: SkillGraph,
    parked: Collection[str],
    daily_budget: int,
    as_of_date: date,
    ruleset: ModuleType,
) -> list[ProposedAction]:
    """§8: suspend down to 7 x cap when backlog > 14 x cap (never T1); resume <= 3 below 3 x cap."""
    cap = revision_cap(daily_budget, ruleset)
    extra = int(ruleset.REINFORCE_EXTRA_MINUTES)
    due = backlog_items(items, parked, as_of_date)
    backlog = sum(i.total_minutes(extra) for i in due)

    def importance(i: RevisionItem) -> int:
        spec = graph.skills.get(i.skill)
        return spec.importance if spec else 0

    def tier(i: RevisionItem) -> str:
        spec = graph.skills.get(i.skill)
        return spec.tier if spec else "T4"

    actions: list[ProposedAction] = []
    if backlog > ruleset.TRIAGE_TRIGGER_MULTIPLE * cap:
        order = sorted(
            (i for i in due if tier(i) != "T1"),
            key=lambda i: (importance(i), i.lapses, -(i.due_date or as_of_date).toordinal(), i.item_key),
        )
        for item in order:
            if backlog <= ruleset.TRIAGE_TARGET_MULTIPLE * cap:
                break
            actions.append(ProposedAction(item.item_key, "SUSPEND", "BACKLOG_TRIAGE"))
            backlog -= item.total_minutes(extra)
    elif backlog < ruleset.RESUME_BELOW_MULTIPLE * cap:
        suspended = sorted(
            (
                i
                for i in items.values()
                if i.state == "SUSPENDED" and i.suspend_reason == "BACKLOG_TRIAGE" and i.skill not in parked
            ),
            key=lambda i: (
                -importance(i),
                -i.lapses,
                (i.due_before_suspension or as_of_date).toordinal(),
                i.item_key,
            ),
        )
        actions.extend(
            ProposedAction(i.item_key, "RESUME", "BACKLOG_TRIAGE")
            for i in suspended[: ruleset.RESUME_MAX_PER_DAY]
        )
    return actions


def revision_facts(projection: RevisionProjection, as_of: date) -> dict[str, tuple[int, bool, bool]]:
    """§9 gap-engine facts per skill: (max_active_lapses, has_overdue_item, has_leech)."""
    facts: dict[str, tuple[int, bool, bool]] = {}
    for item in projection.items.values():
        lapses, overdue, leech = facts.get(item.skill, (0, False, False))
        if item.state == "ACTIVE":
            lapses = max(lapses, item.lapses)
            overdue = overdue or (item.due_date is not None and item.due_date < as_of)
        if item.state == "SUSPENDED" and item.suspend_reason == "LEECH":
            leech = True
        facts[item.skill] = (lapses, overdue, leech)
    return facts


def revision_health(
    projection: RevisionProjection,
    graph: SkillGraph,
    parked: Collection[str],
    as_of: date,
    ruleset: ModuleType,
    window_days: int = 30,
) -> RevisionHealth:
    """§9 readiness G7 inputs: ACTIVE T1/T2 items (not parked) overdue > 7 days; 30-day review pass rate."""
    overdue = sorted(
        i.item_key
        for i in projection.items.values()
        if i.state == "ACTIVE"
        and i.skill not in parked
        and (spec := graph.skills.get(i.skill)) is not None
        and spec.tier in ("T1", "T2")
        and i.days_overdue(as_of) > ruleset.G7_OVERDUE_DAYS
    )
    recent = [r for r in projection.reviews if 0 <= (as_of - r.reviewed_on).days < window_days]
    passes = sum(1 for r in recent if r.outcome == "PASS")
    return RevisionHealth(
        overdue_t1_t2_over_7d=len(overdue),
        overdue_items=tuple(overdue),
        pass_rate_30d=100 * passes // len(recent) if recent else None,
        reviews_30d=len(recent),
        passes_30d=passes,
    )


def row_facts(rows: Sequence[tuple[str, int, int | None, bool, int | None]]) -> tuple[RowFact, ...]:
    return tuple(
        RowFact(skill, level, points, scoring, ratio) for skill, level, points, scoring, ratio in rows
    )
