"""Revision engine values (REVISION_ENGINE.md). Immutable; the projection replays events into items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class RowFact:
    """One evidence row of an observation, as the revision engine needs it."""

    skill: str
    level: int
    outcome_points: int | None
    is_scoring: bool
    time_ratio_bp: int | None = None


@dataclass(frozen=True)
class ProblemFact:
    id: int
    difficulty: str
    is_canonical: bool
    is_catalog: bool  # personal problems never get PROBLEM items ("applies to catalog problems")
    primary_skill: str | None


@dataclass(frozen=True)
class RevisionObservation:
    """A current observation reduced to the facts revision rules read (§3 triggers, §5 outcomes)."""

    source_type: str  # ATTEMPT | ASSESSMENT | MOCK_ROUND
    source_id: int
    observed_on: date
    observed_at: datetime
    rows: tuple[RowFact, ...]
    revision_item_key: str | None = None
    problem: ProblemFact | None = None  # attempts only
    outcome: str | None = None  # attempts: PASS/PARTIAL/FAIL
    hints_used: int = 0
    solution_viewed: bool = False
    time_seconds: int | None = None
    kind: str | None = None  # assessment kind
    source_key: str | None = None


@dataclass(frozen=True)
class RevisionAction:
    """A recorded decision (revision_item_actions): SUSPEND / RESUME with reason MANUAL / BACKLOG_TRIAGE."""

    id: int
    item_key: str
    action: str
    reason: str
    action_on: date
    created_at: datetime


@dataclass(frozen=True)
class RevisionItem:
    item_key: str
    item_type: str  # PROBLEM | PATTERN | CS | CONCEPT | SD | BEHAVIORAL | MOCK_WEAKNESS
    skill: str
    subject_ref: str
    ladder: str  # STANDARD | MOCKW
    state: str  # ACTIVE | SUSPENDED | GRADUATED
    suspend_reason: str | None
    interval_index: int
    due_date: date | None  # GRADUATED: next maintenance check (T1/T2) or None
    lapses: int
    needs_reinforcement: bool
    created_on: date
    last_reviewed_on: date | None
    minutes: int  # base minutes (reinforcement adds REINFORCE_EXTRA_MINUTES)
    suspended_on: date | None = None
    suspended_at: datetime | None = None
    due_before_suspension: date | None = None

    def total_minutes(self, reinforce_extra: int) -> int:
        """Item minutes, + the reinforcement refresh when ``needs_reinforcement`` (§5)."""
        return self.minutes + (reinforce_extra if self.needs_reinforcement else 0)

    def is_due(self, as_of: date) -> bool:
        return self.due_date is not None and self.due_date <= as_of

    def days_overdue(self, as_of: date) -> int:
        return max((as_of - self.due_date).days, 0) if self.due_date is not None else 0


@dataclass(frozen=True)
class Review:
    item_key: str
    skill: str
    reviewed_on: date
    outcome: str  # PASS | PARTIAL | FAIL
    maintenance: bool
    source_type: str
    source_id: int


@dataclass(frozen=True)
class RevisionProjection:
    items: dict[str, RevisionItem]
    reviews: tuple[Review, ...]


@dataclass(frozen=True)
class ProposedAction:
    """An action the engine wants recorded (triage / auto-resume); the service persists it."""

    item_key: str
    action: str
    reason: str


@dataclass(frozen=True)
class RevisionHealth:
    overdue_t1_t2_over_7d: int
    overdue_items: tuple[str, ...]
    pass_rate_30d: int | None
    reviews_30d: int
    passes_30d: int
