"""Personal roadmap (D-080): a read-only classification of the gap engine's output into build / consolidate /
sharpen / maintain / parked / unmeasured, plus a plain "what changed" comparison of two engine evaluations.

There is no second roadmap engine: every input is the engines' own output (gaps, skill states, skill graph);
this module only groups it. Pure and deterministic: no clock, no I/O, ordering follows the gap engine's rank.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.gaps.model import Gap, GapReport
from app.domain.profile.model import SkillGraph
from app.domain.skills.state import SkillState

BUILD = "build"  # fundamentals or a prerequisite are missing
CONSOLIDATE = "consolidate"  # partial, inconsistent understanding
SHARPEN = "sharpen"  # understood; timed / interview performance next
MAINTAIN = "maintain"  # at or above target: periodic revision only
PARKED = "parked"  # not worth time for the current target and date
UNMEASURED = "unmeasured"  # no evidence yet
BUCKETS = (BUILD, CONSOLIDATE, SHARPEN, MAINTAIN, PARKED, UNMEASURED)

BUILD_STAGES = ("LEARN", "DIAGNOSE", "PREREQUISITE")
SHARPEN_STAGES = ("TIMED", "EXPLAIN", "TRANSFER", "SIMULATE", "THINK_ALOUD")
FOCUS_SIZE = 5
WHY_SIZE = 3


def roadmap_bucket(gap: Gap, state: SkillState | None) -> str:
    if gap.status == "PARKED":
        return PARKED
    if state is None or not state.assessed:
        return UNMEASURED
    if gap.status == "NONE":
        return MAINTAIN
    if gap.status == "BLOCKED" or gap.focus_stage in BUILD_STAGES or not state.level:
        return BUILD
    if gap.focus_stage in SHARPEN_STAGES:
        return SHARPEN
    return CONSOLIDATE


def skill_health(gap: Gap, state: SkillState | None) -> str:
    """strong / developing / critical / unknown / parked, for the "your current state" snapshot."""
    if gap.status == "PARKED":
        return "parked"
    if state is None or not state.assessed:
        return "unknown"
    if gap.status == "NONE":
        return "strong"
    return "critical" if gap.status == "CRITICAL" else "developing"


@dataclass(frozen=True)
class Prerequisite:
    skill: str
    score: int | None
    min_score: int
    satisfied: bool


@dataclass(frozen=True)
class RoadmapItem:
    skill_key: str
    component: str
    bucket: str
    health: str
    score: int | None  # effective score
    target: int
    status: str
    priority: int
    rank: int
    level: int | None
    confidence: str
    declared_unknown: bool  # the only self-report that enters a state: "new to me" counts as measured at 0
    primary_gap_type: str | None
    focus_stage: str | None
    focus_skill: str | None
    reason_codes: tuple[str, ...]
    importance: int
    prerequisites: tuple[Prerequisite, ...]  # only the unsatisfied ones
    metrics: Mapping[str, object]


@dataclass(frozen=True)
class PersonalRoadmap:
    items: tuple[RoadmapItem, ...]  # engine rank order
    focus_now: tuple[RoadmapItem, ...]
    counts: Mapping[str, int]
    health_counts: Mapping[str, int]

    def bucket(self, name: str) -> tuple[RoadmapItem, ...]:
        return tuple(i for i in self.items if i.bucket == name)

    @property
    def later(self) -> tuple[RoadmapItem, ...]:
        focus = {i.skill_key for i in self.focus_now}
        return tuple(
            i for i in self.items if i.bucket in (BUILD, CONSOLIDATE, SHARPEN) and i.skill_key not in focus
        )


def unsatisfied_prerequisites(
    skill_key: str, graph: SkillGraph, states: Mapping[str, SkillState]
) -> tuple[Prerequisite, ...]:
    spec = graph.skills.get(skill_key)
    if spec is None:
        return ()
    out = []
    for prereq, min_score in spec.prerequisites:
        state = states.get(prereq)
        score = state.score if state is not None else None
        if score is None or score < min_score:
            out.append(Prerequisite(prereq, score, min_score, False))
    return tuple(out)


def build_personal_roadmap(
    gaps: GapReport, states: Mapping[str, SkillState], graph: SkillGraph
) -> PersonalRoadmap:
    items = []
    for gap in gaps.gaps:  # already ranked by the gap engine
        state = states.get(gap.skill_key)
        items.append(
            RoadmapItem(
                skill_key=gap.skill_key,
                component=gap.component,
                bucket=roadmap_bucket(gap, state),
                health=skill_health(gap, state),
                score=gap.effective_score,
                target=gap.target_score,
                status=gap.status,
                priority=gap.priority,
                rank=gap.rank,
                level=gap.level,
                confidence=gap.confidence,
                declared_unknown=bool(state and state.declared_unknown),
                primary_gap_type=gap.primary_gap_type,
                focus_stage=gap.focus_stage,
                focus_skill=gap.focus_skill,
                reason_codes=gap.reason_codes,
                importance=gap.importance,
                prerequisites=unsatisfied_prerequisites(gap.skill_key, graph, states),
                metrics=dict(gap.metrics),
            )
        )
    # BLOCKED skills get no missions (priority flows to the prerequisite): never "focus now".
    focus = tuple(i for i in items if i.bucket in (BUILD, CONSOLIDATE, SHARPEN) and i.status != "BLOCKED")[
        :FOCUS_SIZE
    ]
    counts = {b: sum(1 for i in items if i.bucket == b) for b in BUCKETS}
    health = {
        h: sum(1 for i in items if i.health == h)
        for h in ("strong", "developing", "critical", "unknown", "parked")
    }
    return PersonalRoadmap(tuple(items), focus, counts, health)


@dataclass(frozen=True)
class FocusChange:
    skill_key: str
    priority_before: int | None
    priority_after: int | None
    reason_codes: tuple[
        str, ...
    ]  # the engine's reasons for the skill's current state (entered) or last state (left)


@dataclass(frozen=True)
class RoadmapChanges:
    entered: tuple[FocusChange, ...]  # now in the focus list
    left: tuple[FocusChange, ...]  # no longer in the focus list

    @property
    def changed(self) -> bool:
        return bool(self.entered or self.left)


def roadmap_changes(previous: PersonalRoadmap, current: PersonalRoadmap) -> RoadmapChanges:
    """Which skills entered or left the focus list between two evaluations of the same engines.

    With nothing in focus before (the first measurements), there is nothing to compare: no change is reported.
    """
    if not previous.focus_now:
        return RoadmapChanges((), ())
    before = {i.skill_key: i for i in previous.focus_now}
    after = {i.skill_key: i for i in current.focus_now}
    prev_all = {i.skill_key: i for i in previous.items}
    cur_all = {i.skill_key: i for i in current.items}
    entered = tuple(
        FocusChange(
            k,
            prev_all[k].priority if k in prev_all else None,
            after[k].priority,
            after[k].reason_codes,
        )
        for k in after
        if k not in before
    )
    left = tuple(
        FocusChange(
            k,
            before[k].priority,
            cur_all[k].priority if k in cur_all else None,
            before[k].reason_codes,
        )
        for k in before
        if k not in after
    )
    return RoadmapChanges(entered, left)


def focus_keys(items: Sequence[RoadmapItem]) -> list[str]:
    return [i.skill_key for i in items]
