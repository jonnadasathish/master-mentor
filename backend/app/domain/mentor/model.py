"""Mentor engine inputs and outputs (MENTOR_ENGINE.md §1, §11). Immutable values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.domain.baseline.calibration import CalibrationStatus
from app.domain.catalog.model import Milestone, MissionTemplate
from app.domain.gaps.model import GapReport, SkillFacts
from app.domain.profile.model import ProfileSpec, SkillGraph
from app.domain.readiness.components import ComponentScores
from app.domain.revision.model import RevisionProjection
from app.domain.skills.state import SkillState

READINESS_ORDER = ("NOT_MEASURED", "FOUNDATION", "DEVELOPING", "INTERVIEW_READY", "STRONG")


@dataclass(frozen=True)
class Blocker:
    gate: str
    message: str
    component: str | None = None
    skill: str | None = None
    actual: object = None
    required: object = None


@dataclass(frozen=True)
class ReadinessView:
    """What the mentor reads from readiness (READINESS_MODEL §10)."""

    state: str = "NOT_MEASURED"
    blockers: tuple[Blocker, ...] = ()
    simulation_eligible: bool = False
    lapsed: bool = False
    weighted_score: int = 0

    def at_least(self, state: str) -> bool:
        return READINESS_ORDER.index(self.state) >= READINESS_ORDER.index(state)


@dataclass(frozen=True)
class ProblemInfo:
    id: int
    platform_key: str
    difficulty: str
    is_canonical: bool
    skills: tuple[tuple[str, int], ...]  # (skill, mapping_weight_bp)
    attempt_count: int = 0
    last_attempt_on: date | None = None

    def primary(self) -> str | None:
        return next((s for s, bp in self.skills if bp == 10000), None)


@dataclass(frozen=True)
class PlanHistoryItem:
    plan_date: date
    skill: str | None
    stage: str | None
    candidate_type: str
    status: str  # PENDING | DONE | SKIPPED | DEFERRED | DISCARDED
    skip_reason: str | None = None


@dataclass(frozen=True)
class CarriedItem:
    """Yesterday's DEFERRED item, re-offered once with +5."""

    item_id: int
    candidate_type: str
    candidate_key: str
    skill: str | None
    stage: str | None
    template_key: str | None
    minutes: int
    score: int
    problem_ids: tuple[int, ...] = ()
    revision_item_key: str | None = None
    battery_item_key: str | None = None
    already_carried: bool = False


@dataclass(frozen=True)
class MockRoundInfo:
    id: int
    round_type: str
    occurred_on: date


@dataclass(frozen=True)
class PracticeSummary:
    """Practice minutes (§5 definition) aggregated for the plan date."""

    track_minutes_7d: Mapping[str, int] = field(default_factory=dict)
    skill_minutes_7d: Mapping[str, int] = field(default_factory=dict)
    skill_minutes_14d: Mapping[str, int] = field(default_factory=dict)
    study_minutes_7d: Mapping[str, int] = field(default_factory=dict)
    total_minutes_14d: int = 0


@dataclass(frozen=True)
class ExitFacts:
    """Counts for milestone extra exit criteria (seed/roadmap.yaml extra_exit)."""

    machine_coding_passes: int = 0  # MACHINE_CODING >= 70 on distinct exercises
    timed_sd_passes: int = 0  # timed SD_DESIGN >= 70 on distinct exercises
    stories_per_skill: Mapping[str, int] = field(default_factory=dict)
    g6_passes: bool = False


@dataclass(frozen=True)
class PlanInputs:
    as_of: date
    budget: int
    phase: str
    weeks_left: Decimal | None
    target_date: date | None
    goal_exists: bool
    calibration: CalibrationStatus
    gaps: GapReport
    states: Mapping[str, SkillState]
    facts: Mapping[str, SkillFacts]
    components: ComponentScores
    graph: SkillGraph
    profile: ProfileSpec
    revision: RevisionProjection
    templates: tuple[MissionTemplate, ...]
    problems: tuple[ProblemInfo, ...]
    milestones: tuple[Milestone, ...]
    readiness: ReadinessView = ReadinessView()
    plan_history: tuple[PlanHistoryItem, ...] = ()
    practice: PracticeSummary = PracticeSummary()
    carried_over: tuple[CarriedItem, ...] = ()
    mock_rounds: tuple[MockRoundInfo, ...] = ()
    exit_facts: ExitFacts = ExitFacts()
    triage_suspended_today: tuple[str, ...] = ()
    component_scores_28d_ago: Mapping[str, int] | None = None
    blocked_problem_ids: frozenset[int] = frozenset()  # already used today (regenerate keeps them out)
    done_minutes: int = 0  # regenerate: minutes of kept DONE/SKIPPED items
    kept_items: int = 0
    kept_skills: frozenset[str] = frozenset()
    kept_keys: frozenset[str] = frozenset()  # regenerate: candidates already DONE/SKIPPED today


@dataclass(frozen=True)
class Explanation:
    current: int | None
    effective: int | None
    target: int | None
    priority: int | None
    evidence: str
    expected_outcome: str


@dataclass(frozen=True)
class PlanItem:
    position: int
    candidate_type: (
        str  # BASELINE | GAP | DIAGNOSTIC | REVISION | MAINTENANCE | MOCK | FINAL_SIMULATION | FOLLOW_UP
    )
    candidate_key: str
    skill: str | None
    template_key: str | None
    stage: str | None
    minutes: int
    score: int
    problem_ids: tuple[int, ...] = ()
    revision_item_key: str | None = None
    battery_item_key: str | None = None
    round_type: str | None = None
    reason_codes: tuple[str, ...] = ()
    explanation: Explanation | None = None
    carried_over_from_id: int | None = None


@dataclass(frozen=True)
class StopEntry:
    skill: str
    code: str  # PARKED_DEADLINE | NOT_FEASIBLE | OVER_TARGET | STUDIED_NOT_TESTED
    instruction: str
    minutes_7d: int = 0


@dataclass(frozen=True)
class Dropped:
    key: str
    reason: str
    detail: str | None = None


@dataclass(frozen=True)
class Message:
    rule: str
    text: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class DailyPlan:
    plan_date: date
    budget_minutes: int
    allocated_minutes: int
    unallocated_minutes: int
    phase: str
    calibration_mode: bool
    items: tuple[PlanItem, ...]
    stop_list: tuple[StopEntry, ...]
    dropped: tuple[Dropped, ...]
    message: Message
