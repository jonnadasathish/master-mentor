"""Per-skill facts for the gap decision table, from evidence rows (GAP_ENGINE.md §5-§6, §9). Pure."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import ModuleType

from app.domain.evidence.model import EvidenceRow
from app.domain.gaps.model import EvidenceRef, SkillFacts
from app.domain.skills.state import qualified_level


@dataclass(frozen=True)
class MockRoundSummary:
    """One mock round: when it happened and which skills it flagged ``is_weakness``."""

    id: int
    occurred_on: date
    weakness_skills: tuple[str, ...]


def mock_weakness_skills(rounds: Sequence[MockRoundSummary], as_of: date, ruleset: ModuleType) -> set[str]:
    """Skills flagged in the last 3 rounds (all types, newest first), only rounds <= 60 days old."""
    recent = [
        r
        for r in rounds
        if r.occurred_on <= as_of and (as_of - r.occurred_on).days <= ruleset.MOCK_WINDOW_DAYS
    ]
    recent.sort(key=lambda r: (r.occurred_on, r.id), reverse=True)
    return {skill for r in recent[: ruleset.MOCK_WINDOW_ROUNDS] for skill in r.weakness_skills}


def _ref(r: EvidenceRow) -> EvidenceRef:
    return (r.source_type, r.source_id)


def _points(r: EvidenceRow) -> int:
    return r.outcome_points or 0


def _mean(values: Sequence[int]) -> Decimal | None:
    return Decimal(sum(values)) / Decimal(len(values)) if values else None


def _median(values: Sequence[int]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return Decimal(ordered[mid])
    return Decimal(ordered[mid - 1] + ordered[mid]) / Decimal(2)


def build_skill_facts(
    rows: Sequence[EvidenceRow], as_of: date, ruleset: ModuleType, *, mock_weakness: bool = False
) -> SkillFacts:
    """``rows`` = every evidence row of one skill (any order); rows observed after ``as_of`` are ignored."""
    visible = sorted((r for r in rows if r.observed_on <= as_of), key=lambda r: r.order_key, reverse=True)
    scoring = [r for r in visible if r.is_scoring]

    last5 = scoring[: ruleset.FAILURE_WINDOW_ROWS]
    fails = [r for r in last5 if _points(r) < ruleset.FAILURE_BELOW_POINTS]

    pattern = [
        r
        for r in scoring
        if r.source_type == "ATTEMPT"
        and r.rule == "MAPPED"
        and r.is_primary
        and r.is_unseen
        and r.pattern_identified is not None
    ][: ruleset.PATTERN_WINDOW_ATTEMPTS]
    misses = [r for r in pattern if r.pattern_identified is False]

    l1 = [r for r in scoring if r.level == 1]

    timed_points = [
        r for r in scoring if r.time_ratio_bp is not None and _points(r) >= ruleset.SPEED_MIN_POINTS
    ][: ruleset.SPEED_WINDOW_ROWS]
    timed = [r for r in scoring if r.timed and r.within_limit is not None][: ruleset.SPEED_WINDOW_ROWS]

    depth = [r for r in scoring if r.depth_points is not None][: ruleset.DEPTH_WINDOW_ROWS]
    comm = [r for r in scoring if r.communication_points is not None][: ruleset.COMMUNICATION_WINDOW_ROWS]

    rated = [r for r in scoring if r.self_rating_before is not None][: ruleset.CONFIDENCE_GAP_WINDOW_ROWS]
    over = [
        r
        for r in rated
        if (r.self_rating_before or 0) >= ruleset.OVERCONFIDENT_MIN_RATING
        and _points(r) < ruleset.OVERCONFIDENT_BELOW_POINTS
    ]
    under = [
        r
        for r in rated
        if (r.self_rating_before or 99) <= ruleset.UNDERCONFIDENT_MAX_RATING
        and _points(r) >= ruleset.UNDERCONFIDENT_MIN_POINTS
    ]

    mocks = [r for r in scoring if r.source_type == "MOCK_ROUND"]
    latest_mock = (
        mocks[0].outcome_points
        if mocks and (as_of - mocks[0].observed_on).days <= ruleset.INTERVIEW_EXECUTION_WINDOW_DAYS
        else None
    )
    non_mock = [r for r in scoring if r.level != 7]
    level_without_mocks = qualified_level(non_mock, as_of, ruleset) if scoring else None

    studies = [
        r
        for r in visible
        if r.kind == "STUDY_SESSION" and (as_of - r.observed_on).days <= ruleset.STUDIED_NOT_TESTED_DAYS
    ]
    studied_not_tested = bool(studies) and not any(r.observed_on >= studies[0].observed_on for r in scoring)

    return SkillFacts(
        days_since_last_practice=(as_of - scoring[0].observed_on).days if scoring else None,
        scoring_rows=len(scoring),
        n_fail_last5=len(fails),
        fail_refs=tuple(_ref(r) for r in fails),
        pattern_misses_last4=len(misses),
        pattern_refs=tuple(_ref(r) for r in misses),
        l1_rows=len(l1),
        l1_recent_mean=_mean([_points(r) for r in l1[:2]]) if len(l1) >= 2 else None,
        speed_median_ratio_bp=_median([r.time_ratio_bp or 0 for r in timed_points]),
        timed_over_limit_last3=sum(1 for r in timed if r.within_limit is False),
        speed_refs=tuple(_ref(r) for r in timed_points),
        depth_mean_last3=_mean([r.depth_points or 0 for r in depth]),
        depth_refs=tuple(_ref(r) for r in depth),
        communication_mean_last3=_mean([r.communication_points or 0 for r in comm]),
        communication_outcome_mean_last3=_mean([_points(r) for r in comm]),
        communication_refs=tuple(_ref(r) for r in comm),
        overconfident_rows=len(over),
        underconfident_rows=len(under),
        underconfident_ratings=tuple(r.self_rating_before or 0 for r in under),
        confidence_refs=tuple(_ref(r) for r in over),
        level_without_mocks=level_without_mocks,
        latest_mock_points_60d=latest_mock,
        has_l6_row=any(r.level == 6 for r in scoring),
        studied_not_tested=studied_not_tested,
        mock_weakness=mock_weakness,
        last3_points=tuple(_points(r) for r in scoring[:3]),
    )


def build_all_facts(
    skills: Sequence[str],
    rows: Sequence[EvidenceRow],
    as_of: date,
    ruleset: ModuleType,
    mock_weakness: set[str] | None = None,
) -> Mapping[str, SkillFacts]:
    by_skill: dict[str, list[EvidenceRow]] = {s: [] for s in skills}
    for r in rows:
        if r.skill in by_skill:
            by_skill[r.skill].append(r)
    weak = mock_weakness or set()
    return {s: build_skill_facts(by_skill[s], as_of, ruleset, mock_weakness=s in weak) for s in skills}
