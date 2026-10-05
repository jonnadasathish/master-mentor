"""Observation -> evidence rows, exactly as EVIDENCE_MODEL.md §4-§6 (ruleset passed in, no clock, no I/O).

One row per (source, skill). When several rules target the same skill for one observation, the row keeps
the minimum outcome points and every other attribute from the highest-precedence rule
(MAPPED > DERIVED in table order > MISTAKE).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from types import ModuleType

from app.domain.evidence.model import (
    AssessmentObservation,
    AttemptObservation,
    EvidenceRow,
    MockRoundObservation,
    SkillInfo,
)

PRACTICE_KINDS = frozenset(
    {
        "CONCEPT_EXPLAIN",
        "CODE_EXERCISE",
        "ESTIMATION_DRILL",
        "SD_DESIGN",
        "LLD_DESIGN",
        "MACHINE_CODING",
        "STORY_REHEARSAL",
        "PROJECT_WALKTHROUGH",
    }
)
PATTERN_RECOGNITION = "dsa.pattern_recognition"


def derive_evidence(
    *,
    attempts: Sequence[AttemptObservation],
    assessments: Sequence[AssessmentObservation],
    mock_rounds: Sequence[MockRoundObservation],
    skills: Mapping[str, SkillInfo],
    ruleset: ModuleType,
) -> list[EvidenceRow]:
    """Every evidence row for the given current observations, in a deterministic order."""
    rows: list[EvidenceRow] = []
    rows.extend(_attempt_rows(attempts, ruleset))
    rows.extend(r for a in assessments for r in _assessment_rows(a, skills, ruleset))
    rows.extend(r for m in mock_rounds for r in _mock_rows(m, ruleset))
    known = [r for r in rows if r.skill in skills]
    return sorted(known, key=lambda r: (r.order_key, r.skill))


# --------------------------------------------------------------------------------------------- attempts


def outcome_points(a: AttemptObservation, ruleset: ModuleType) -> int:
    p = ruleset.OUTCOME_POINTS
    if a.outcome == "FAIL":
        return int(p["FAIL"])
    if a.solution_viewed:
        return int(p["SOLUTION_VIEWED"])
    if a.outcome == "PARTIAL":
        return int(p["PARTIAL"])
    if a.hints_used >= 2:
        return int(p["PASS_2_PLUS_HINTS"])
    if a.hints_used == 1:
        return int(p["PASS_1_HINT"])
    return int(p["PASS_NO_HINTS"])


def expected_seconds(a: AttemptObservation, ruleset: ModuleType) -> int:
    minutes = a.expected_minutes or int(ruleset.DEFAULT_EXPECTED_MINUTES[a.difficulty])
    return minutes * 60


def attempt_level(a: AttemptObservation, prior: Sequence[AttemptObservation], ruleset: ModuleType) -> int:
    """EVIDENCE_MODEL §5.1: ladder first, then caps (EASY, seen-before)."""
    if a.solution_viewed or a.hints_used >= 1:
        level = 2
    else:
        level = 3
        limit = a.time_limit_seconds
        if (
            a.timed
            and a.time_seconds is not None
            and limit is not None
            and a.time_seconds <= limit
            and limit <= expected_seconds(a, ruleset)
            and a.difficulty in ("MEDIUM", "HARD")
        ):
            level = 4
        if (
            level == 4
            and (a.explanation_score or 0) >= ruleset.L5_MIN_EXPLANATION_SCORE
            and a.complexity_correct
        ):
            level = 5
        if level == 5 and (a.difficulty == "HARD" or a.followup_solved is True):
            level = 6
    if a.difficulty == "EASY":
        level = min(level, ruleset.EASY_LEVEL_CAP)
    if not is_unseen(a, prior):
        if not prior:
            level = min(level, ruleset.SEEN_PROBLEM_LEVEL_CAP)  # seen elsewhere only
        elif (a.attempted_on - prior[-1].attempted_on).days >= ruleset.SEEN_RECENT_DAYS:
            level = min(level, ruleset.SEEN_PROBLEM_LEVEL_CAP)
        else:
            level = min(level, ruleset.SEEN_RECENT_LEVEL_CAP)
    return level


def is_unseen(a: AttemptObservation, prior: Sequence[AttemptObservation]) -> bool:
    return not prior and not a.seen_elsewhere


def _attempt_rows(attempts: Sequence[AttemptObservation], ruleset: ModuleType) -> Iterable[EvidenceRow]:
    by_problem: dict[int, list[AttemptObservation]] = {}
    for a in sorted(attempts, key=lambda x: (x.attempted_at, x.id)):
        prior = by_problem.setdefault(a.problem_id, [])
        yield from _rows_for_attempt(a, list(prior), ruleset)
        prior.append(a)


def _rows_for_attempt(
    a: AttemptObservation, prior: list[AttemptObservation], ruleset: ModuleType
) -> list[EvidenceRow]:
    level = attempt_level(a, prior, ruleset)
    unseen = is_unseen(a, prior)
    limit = a.time_limit_seconds if (a.timed and a.time_limit_seconds) else expected_seconds(a, ruleset)
    within: bool | None = None
    if a.timed and a.time_seconds is not None and a.time_limit_seconds:
        within = a.time_seconds <= a.time_limit_seconds
    rubric = dict(a.execution_rubric or {})
    think_aloud = rubric.get("think_aloud")
    base = EvidenceRow(
        source_type="ATTEMPT",
        source_id=a.id,
        skill="",
        rule="MAPPED",
        level=level,
        outcome_points=outcome_points(a, ruleset),
        is_scoring=True,
        observed_on=a.attempted_on,
        observed_at=a.attempted_at,
        difficulty_bp=int(ruleset.DIFFICULTY_BP[a.difficulty]),
        mapping_bp=int(ruleset.MAPPING_BP_DERIVED),
        source_key=f"problem:{a.problem_id}",
        timed=a.timed,
        time_ratio_bp=a.time_seconds * 10000 // limit if a.time_seconds is not None else None,
        within_limit=within,
        self_rating_before=a.self_rating_before,
        is_unseen=unseen,
        kind="ATTEMPT",
    )
    candidates: list[EvidenceRow] = [
        replace(
            base,
            skill=skill,
            mapping_bp=weight,
            is_primary=weight == ruleset.MAPPING_BP_PRIMARY,
            depth_points=a.explanation_score * 10 if a.explanation_score is not None else None,
            communication_points=think_aloud * 10 if think_aloud is not None else None,
            pattern_identified=a.pattern_identified,
        )
        for skill, weight in a.mappings  # MAPPED
    ]

    def derived(skill: str, pts: int, lvl: int, communication: int | None = None) -> None:
        candidates.append(
            replace(
                base,
                skill=skill,
                rule="DERIVED",
                level=lvl,
                outcome_points=pts,
                communication_points=communication,
            )
        )

    if a.pattern_identified is not None and unseen:  # §5.2 rows, in table order
        pr_level = 3
        if a.timed:
            pr_level = 4
            if (a.explanation_score or 0) >= ruleset.L5_MIN_EXPLANATION_SCORE:
                pr_level = 5
        derived(PATTERN_RECOGNITION, 100 if a.pattern_identified else 0, pr_level)
    if a.complexity_correct is not None:
        derived("dsa.complexity_analysis", 100 if a.complexity_correct else 0, level)
    if a.followup_solved is not None:
        derived("execution.followup_handling", 100 if a.followup_solved else 0, level)
    for dimension, skill in ruleset.EXECUTION_RUBRIC_SKILLS.items():
        if dimension in rubric:
            value = rubric[dimension] * 10
            derived(skill, value, level, communication=value if dimension == "think_aloud" else None)
    if a.outcome in ("PASS", "PARTIAL") and a.hints_used == 0 and a.pattern_identified is not False:
        bug = any(m in ruleset.BUG_CLASS_MISTAKES for m in a.mistakes)
        derived("execution.bug_free_coding", 0 if a.outcome == "PARTIAL" else (50 if bug else 100), level)
    for code in a.mistakes:  # §5.3 MISTAKE rows
        for skill in ruleset.MISTAKE_ROUTING.get(code, ()):
            candidates.append(replace(base, skill=skill, rule="MISTAKE", outcome_points=0))
    return _merge(candidates)


def _merge(candidates: Sequence[EvidenceRow]) -> list[EvidenceRow]:
    """One row per skill: attributes of the first (highest-precedence) rule, minimum outcome points."""
    merged: dict[str, EvidenceRow] = {}
    for row in candidates:
        first = merged.get(row.skill)
        if first is None:
            merged[row.skill] = row
        elif row.outcome_points is not None and (
            first.outcome_points is None or row.outcome_points < first.outcome_points
        ):
            merged[row.skill] = replace(first, outcome_points=row.outcome_points)
    return list(merged.values())


# --------------------------------------------------------------------------------------------- assessments


def assessment_level(a: AssessmentObservation, skill: str, points: int | None, ruleset: ModuleType) -> int:
    """EVIDENCE_MODEL §5.4. Returns 0 for non-scoring kinds."""
    if a.kind in ("STUDY_SESSION", "SELF_ASSESSMENT"):
        return 0
    if a.kind == "RECALL_QUIZ":
        return 0 if a.notes_used else 1
    within = (
        a.timed
        and a.time_seconds is not None
        and a.time_limit_seconds is not None
        and a.time_seconds <= a.time_limit_seconds
    )
    if a.kind == "PATTERN_DRILL":
        if skill != PATTERN_RECOGNITION:
            return 1
        level = 3
        if within:
            level = 4
            if (a.followup_points or 0) >= ruleset.FOLLOWUP_MIN_POINTS:
                level = 5
        return level
    if a.kind == "APPLIED_TASK":
        ok = (points or 0) >= 70 and (a.followup_points or 0) >= ruleset.FOLLOWUP_MIN_POINTS
        return 6 if ok else 3
    if a.kind in PRACTICE_KINDS:
        level = 2 if (a.notes_used or a.hints_used > 0 or a.reference_used) else 3
        if level == 3 and within:
            level = 4
        if level == 4 and (a.followup_points or 0) >= ruleset.FOLLOWUP_MIN_POINTS:
            level = 5
        if level == 5 and (a.peer_evaluated or a.unseen_variant):
            level = 6
        return level
    raise ValueError(f"unknown assessment kind {a.kind!r}")


def _assessment_rows(
    a: AssessmentObservation, skills: Mapping[str, SkillInfo], ruleset: ModuleType
) -> list[EvidenceRow]:
    rows = []
    within: bool | None = None
    if a.timed and a.time_seconds is not None and a.time_limit_seconds:
        within = a.time_seconds <= a.time_limit_seconds
    ratio = (
        a.time_seconds * 10000 // a.time_limit_seconds
        if (a.time_seconds is not None and a.time_limit_seconds)
        else None
    )
    for s in a.skills:
        level = assessment_level(a, s.skill, s.outcome_points, ruleset)
        scoring = level >= 1 and s.outcome_points is not None
        rows.append(
            EvidenceRow(
                source_type="ASSESSMENT",
                source_id=a.id,
                skill=s.skill,
                rule="ASSESSMENT",
                level=level,
                outcome_points=s.outcome_points if scoring else None,
                is_scoring=scoring,
                observed_on=a.observed_on,
                observed_at=a.observed_at,
                difficulty_bp=int(ruleset.DIFFICULTY_BP[a.difficulty]),
                mapping_bp=s.mapping_weight_bp,
                source_key=a.source_key,
                is_primary=s.mapping_weight_bp == ruleset.MAPPING_BP_PRIMARY,
                timed=a.timed,
                time_ratio_bp=ratio,
                within_limit=within,
                depth_points=a.followup_points,
                communication_points=a.communication_points,
                self_rating_before=a.self_rating_before,
                familiarity=a.familiarity,
                study_minutes=a.study_minutes,
                kind=a.kind,
            )
        )
    return rows


# --------------------------------------------------------------------------------------------- mocks


def _mock_rows(m: MockRoundObservation, ruleset: ModuleType) -> list[EvidenceRow]:
    cap = ruleset.SELF_MOCK_OUTCOME_CAP if m.source == "SELF" else 100
    return [
        EvidenceRow(
            source_type="MOCK_ROUND",
            source_id=m.id,
            skill=s.skill,
            rule="MOCK",
            level=7,
            outcome_points=min(s.outcome_points, cap),
            is_scoring=True,
            observed_on=m.occurred_on,
            observed_at=m.occurred_at,
            difficulty_bp=int(ruleset.DIFFICULTY_BP["MEDIUM"]),
            mapping_bp=ruleset.MAPPING_BP_DERIVED,
            source_key=f"mock_round:{m.id}",
            communication_points=m.communication_points,
            is_weakness=s.is_weakness,
            kind="MOCK",
        )
        for s in m.skills
    ]
