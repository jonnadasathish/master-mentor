"""Skill state from evidence rows (EVIDENCE_MODEL.md §7-§10). Pure: rows + as_of_date + ruleset in, state out.

Rows dated after ``as_of_date`` are ignored, so a state "as of" any past date is reproducible.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from types import ModuleType

from app.domain.evidence.model import EvidenceRow


@dataclass(frozen=True)
class SkillState:
    skill: str
    score: int | None
    level: int | None
    quality: Decimal | None
    confidence: str  # NONE | LOW | MEDIUM | HIGH
    effective_score: int | None
    peak_score: int | None
    evidence_count: int  # scoring rows within the confidence window
    distinct_sources: int
    last_practiced_on: date | None
    last_observed_on: date | None
    label: str
    reality_capped: bool
    declared_unknown: bool
    considered: tuple[EvidenceRow, ...]  # rows that produced the quality (traceability)
    qualifying: tuple[EvidenceRow, ...]  # rows that qualified the level

    @property
    def assessed(self) -> bool:
        return self.confidence != "NONE"


def round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def recency_bp(age_days: int, ruleset: ModuleType) -> int:
    for max_age, bp in ruleset.RECENCY_BP:
        if age_days <= max_age:
            return int(bp)
    return int(ruleset.RECENCY_BP_OLDER)


def _qualified_level(
    rows: Sequence[EvidenceRow], as_of: date, ruleset: ModuleType, *, windowed: bool
) -> tuple[int, tuple[EvidenceRow, ...]]:
    level: int = 0
    qualifying: tuple[EvidenceRow, ...] = ()
    for lvl in range(1, 8):
        needed, distinct, min_points = ruleset.QUALIFICATION[lvl]
        ok = [
            r
            for r in rows
            if r.level >= lvl
            and (r.outcome_points or 0) >= min_points
            and (lvl == 1 or not windowed or (as_of - r.observed_on).days <= ruleset.LEVEL_WINDOW_DAYS)
        ]
        if len(ok) >= needed and len({r.source_key for r in ok}) >= distinct:
            level, qualifying = lvl, tuple(ok)
    return level, qualifying


def qualified_level(rows: Sequence[EvidenceRow], as_of: date, ruleset: ModuleType) -> int:
    """§7.1 level from the given scoring rows (used by the gap engine for "level without mock rows")."""
    return _qualified_level(rows, as_of, ruleset, windowed=True)[0]


def _score(
    rows: Sequence[EvidenceRow], as_of: date, ruleset: ModuleType, *, peak: bool
) -> tuple[int, int, Decimal, tuple[EvidenceRow, ...], tuple[EvidenceRow, ...]]:
    level, qualifying = _qualified_level(rows, as_of, ruleset, windowed=not peak)
    floor_level = max(level - 1, 1)
    considered = tuple(
        r
        for r in rows
        if r.level >= floor_level
        or (
            (r.outcome_points or 0) < ruleset.QUALITY_FAILURE_BELOW_POINTS
            and (as_of - r.observed_on).days <= ruleset.LEVEL_WINDOW_DAYS
        )
    )
    numerator = Decimal(0)
    denominator = Decimal(0)
    for r in considered:
        recency = 10000 if peak else recency_bp((as_of - r.observed_on).days, ruleset)
        weight = Decimal(recency * r.difficulty_bp * r.mapping_bp)
        numerator += Decimal(r.outcome_points or 0) * weight
        denominator += weight
    quality = numerator / denominator if denominator else Decimal(0)
    lo, hi = ruleset.LEVEL_BANDS[level]
    score = round_half_up(Decimal(lo) + Decimal(hi - lo) * quality / Decimal(100))
    return level, score, quality, considered, qualifying


def _label(effective: int | None, ruleset: ModuleType) -> str:
    if effective is None:
        return "UNASSESSED"
    for label, minimum in ruleset.SKILL_LABELS:
        if effective >= minimum:
            return str(label)
    return "WEAK"


def calculate_skill_state(
    skill: str, rows: Sequence[EvidenceRow], as_of: date, ruleset: ModuleType
) -> SkillState:
    visible = sorted(
        (r for r in rows if r.observed_on <= as_of and r.skill == skill), key=lambda r: r.order_key
    )
    scoring = [r for r in visible if r.is_scoring]
    last_observed = max((r.observed_on for r in visible), default=None)

    if not scoring:
        self_assessments = [r for r in visible if r.kind == "SELF_ASSESSMENT"]
        declared = bool(self_assessments) and self_assessments[-1].familiarity == "NONE"
        if declared:
            return SkillState(
                skill,
                0,
                0,
                Decimal(0),
                "LOW",
                0,
                0,
                0,
                0,
                None,
                last_observed,
                _label(0, ruleset),
                False,
                True,
                (),
                (),
            )
        return SkillState(
            skill,
            None,
            None,
            None,
            "NONE",
            None,
            None,
            0,
            0,
            None,
            last_observed,
            "UNASSESSED",
            False,
            False,
            (),
            (),
        )

    level, score, quality, considered, qualifying = _score(scoring, as_of, ruleset, peak=False)
    _, peak, _, _, _ = _score(scoring, as_of, ruleset, peak=True)

    # Interview reality cap: the most recent mock (L7) row, if recent and failing, caps the score.
    capped = False
    mock_rows = [r for r in scoring if r.level == 7]
    if mock_rows:
        latest = mock_rows[-1]
        if (as_of - latest.observed_on).days <= ruleset.REALITY_CAP_WINDOW_DAYS and (
            (latest.outcome_points or 0) < ruleset.REALITY_CAP_BELOW_POINTS
        ):
            if (latest.outcome_points or 0) < score:
                capped = True
            score = min(score, latest.outcome_points or 0)

    window = [r for r in scoring if (as_of - r.observed_on).days <= ruleset.CONFIDENCE_WINDOW_DAYS]
    count, distinct = len(window), len({r.source_key for r in window})
    recent = any((as_of - r.observed_on).days <= ruleset.CONFIDENCE_HIGH["recent_days"] for r in window)
    span = len({r.level for r in window})
    high, medium = ruleset.CONFIDENCE_HIGH, ruleset.CONFIDENCE_MEDIUM
    if (
        count >= high["min_rows"]
        and distinct >= high["min_distinct"]
        and recent
        and span >= high["min_levels"]
    ):
        confidence = "HIGH"
    elif count >= medium["min_rows"] and distinct >= medium["min_distinct"]:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    effective = max(score - int(ruleset.UNCERTAINTY[confidence]), 0)

    return SkillState(
        skill=skill,
        score=score,
        level=level,
        quality=quality,
        confidence=confidence,
        effective_score=effective,
        peak_score=peak,
        evidence_count=count,
        distinct_sources=distinct,
        last_practiced_on=max(r.observed_on for r in scoring),
        last_observed_on=last_observed,
        label=_label(effective, ruleset),
        reality_capped=capped,
        declared_unknown=False,
        considered=considered,
        qualifying=qualifying,
    )


def calculate_skill_states(
    skills: Sequence[str], rows: Sequence[EvidenceRow], as_of: date, ruleset: ModuleType
) -> dict[str, SkillState]:
    by_skill: dict[str, list[EvidenceRow]] = {s: [] for s in skills}
    for r in rows:
        if r.skill in by_skill:
            by_skill[r.skill].append(r)
    return {s: calculate_skill_state(s, by_skill[s], as_of, ruleset) for s in skills}
