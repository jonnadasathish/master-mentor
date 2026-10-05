"""Gap engine inputs (per-skill facts) and outputs (GAP_ENGINE.md §11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

EvidenceRef = tuple[str, int]  # (source_type, source_id)


@dataclass(frozen=True)
class SkillFacts:
    """Numbers the §6 decision table needs, extracted from the skill's evidence rows (gaps/facts.py)."""

    days_since_last_practice: int | None = None  # latest scoring row; None = never practiced
    scoring_rows: int = 0
    n_fail_last5: int = 0
    fail_refs: tuple[EvidenceRef, ...] = ()
    pattern_misses_last4: int = 0
    pattern_refs: tuple[EvidenceRef, ...] = ()
    l1_rows: int = 0  # scoring rows with row level 1
    l1_recent_mean: Decimal | None = None  # mean outcome of the 2 most recent L1 rows
    speed_median_ratio_bp: Decimal | None = None  # last 3 rows with a time and >= 70 points
    timed_over_limit_last3: int = 0
    speed_refs: tuple[EvidenceRef, ...] = ()
    depth_mean_last3: Decimal | None = None
    depth_refs: tuple[EvidenceRef, ...] = ()
    communication_mean_last3: Decimal | None = None
    communication_outcome_mean_last3: Decimal | None = None
    communication_refs: tuple[EvidenceRef, ...] = ()
    overconfident_rows: int = 0
    underconfident_rows: int = 0
    underconfident_ratings: tuple[int, ...] = ()  # self-ratings of the underconfident rows, newest first
    confidence_refs: tuple[EvidenceRef, ...] = ()
    level_without_mocks: int | None = None
    latest_mock_points_60d: int | None = None
    has_l6_row: bool = False
    studied_not_tested: bool = False
    mock_weakness: bool = False  # flagged is_weakness in the last 3 mock rounds (<= 60 days)
    last3_points: tuple[int, ...] = ()  # outcome points of the 3 most recent scoring rows (SUBSTEP_DRILL)


@dataclass(frozen=True)
class RevisionFacts:
    """From the revision projection of the same run (REVISION_ENGINE); empty until Slice 6."""

    max_active_lapses: int = 0
    has_overdue_item: bool = False
    has_leech: bool = False


@dataclass(frozen=True)
class BlockedBy:
    skill: str
    score: int | None
    min_score: int


@dataclass(frozen=True)
class Gap:
    skill_key: str
    component: str
    tier: str
    current_score: int | None
    effective_score: int | None
    level: int | None
    confidence: str
    target_score: int
    floor_score: int
    importance: int
    raw_gap: int | None
    severity: Decimal | None
    pressure_bp: int | None
    priority: int
    status: str
    rank: int
    primary_gap_type: str | None
    gap_types: tuple[str, ...]
    reason_codes: tuple[str, ...]
    blocked_by: tuple[BlockedBy, ...]
    parked_reason: str | None
    focus_stage: str | None
    focus_skill: str | None
    metrics: dict[str, object] = field(default_factory=dict)
    evidence: dict[str, tuple[EvidenceRef, ...]] = field(default_factory=dict)  # reason/type -> rows

    @property
    def actionable(self) -> bool:
        return self.status in ACTIONABLE


ACTIONABLE = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNASSESSED")


@dataclass(frozen=True)
class GapReport:
    as_of_date: object
    phase: str
    weeks_left: Decimal | None
    infeasible_components: tuple[str, ...]
    feasibility_applied: bool
    gaps: tuple[Gap, ...]  # ranked
    feasibility: dict[str, tuple[int, int]] = field(default_factory=dict)  # comp -> (needed, available) min

    def by_skill(self) -> dict[str, Gap]:
        return {g.skill_key: g for g in self.gaps}

    def top_assessed(self, n: int = 3) -> list[Gap]:
        return [g for g in self.gaps if g.actionable and g.status != "UNASSESSED"][:n]
