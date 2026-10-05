"""Observation inputs and evidence outputs of the evidence engine (immutable value objects)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SkillInfo:
    key: str
    component: str
    is_pattern: bool


@dataclass(frozen=True)
class AttemptObservation:
    """A current (non-superseded) problem attempt plus the catalog facts needed to interpret it."""

    id: int
    problem_id: int
    attempted_on: date
    attempted_at: datetime
    outcome: str
    seen_elsewhere: bool
    hints_used: int
    solution_viewed: bool
    pattern_identified: bool | None
    timed: bool
    time_limit_seconds: int | None
    time_seconds: int | None
    explanation_score: int | None
    complexity_correct: bool | None
    followup_solved: bool | None
    execution_rubric: Mapping[str, int] | None
    mistakes: tuple[str, ...]
    self_rating_before: int | None
    difficulty: str
    expected_minutes: int | None  # problem value; None -> ruleset default by difficulty
    mappings: tuple[tuple[str, int], ...]  # (skill_key, mapping_weight_bp)
    mode: str = "PRACTICE"
    revision_item_key: str | None = None
    is_canonical: bool = False
    is_catalog: bool = True  # False for personal problems


@dataclass(frozen=True)
class AssessmentSkillInput:
    skill: str
    outcome_points: int | None
    mapping_weight_bp: int = 10000


@dataclass(frozen=True)
class AssessmentObservation:
    id: int
    kind: str
    observed_on: date
    observed_at: datetime
    source_key: str
    skills: tuple[AssessmentSkillInput, ...]
    notes_used: bool = False
    reference_used: bool = False
    hints_used: int = 0
    timed: bool = False
    time_limit_seconds: int | None = None
    time_seconds: int | None = None
    followup_points: int | None = None
    communication_points: int | None = None
    peer_evaluated: bool = False
    applied: bool = False
    unseen_variant: bool = False
    difficulty: str = "MEDIUM"
    familiarity: str | None = None
    study_minutes: int | None = None
    self_rating_before: int | None = None
    revision_item_key: str | None = None


@dataclass(frozen=True)
class MockRoundSkillInput:
    skill: str
    outcome_points: int
    is_weakness: bool = False


@dataclass(frozen=True)
class MockRoundObservation:
    id: int
    occurred_on: date
    occurred_at: datetime
    source: str  # SELF | PEER | PLATFORM
    round_type: str
    skills: tuple[MockRoundSkillInput, ...]
    communication_points: int | None = None


@dataclass(frozen=True)
class EvidenceRow:
    """One observation's contribution to one skill (EVIDENCE_MODEL §5). Derived; never edited by hand."""

    source_type: str  # ATTEMPT | ASSESSMENT | MOCK_ROUND
    source_id: int
    skill: str
    rule: str  # MAPPED | DERIVED | MISTAKE | ASSESSMENT | MOCK
    level: int
    outcome_points: int | None
    is_scoring: bool
    observed_on: date
    observed_at: datetime
    difficulty_bp: int
    mapping_bp: int
    source_key: str
    is_primary: bool = True
    timed: bool = False
    time_ratio_bp: int | None = None
    within_limit: bool | None = None
    depth_points: int | None = None
    communication_points: int | None = None
    self_rating_before: int | None = None
    pattern_identified: bool | None = None
    is_unseen: bool | None = None
    is_weakness: bool = False
    familiarity: str | None = None
    study_minutes: int | None = None
    kind: str | None = None  # assessment kind, or ATTEMPT / MOCK

    @property
    def order_key(self) -> tuple[date, datetime, str, int]:
        return (self.observed_on, self.observed_at, self.source_type, self.source_id)
