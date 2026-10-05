"""Completion of a content item -> the existing observation it records (LEARNING_ENGINE §4).

No new evidence rule: the result is an assessment payload that goes through AssessmentService exactly like a
hand-logged one, so EVIDENCE_MODEL §5.4 decides its level (STUDY_SESSION L0, RECALL_QUIZ L1 closed-book, the
practice ladder for everything else). Problem types are recorded as ordinary attempts elsewhere.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.domain.learning import grading
from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem


@dataclass(frozen=True)
class Submission:
    """What the learner did. Ratings are 0 / 1 / 2 (missed / partly / fully)."""

    answers: Mapping[str, Sequence[int]] = field(default_factory=dict)  # choice questions: option indexes
    self_grades: Mapping[str, int] = field(default_factory=dict)  # short answers and recall cards
    ratings: Mapping[str, int] = field(
        default_factory=dict
    )  # rubric criteria (by key) / key points (p0, p1…)
    followups: Mapping[str, int] = field(default_factory=dict)  # follow-ups by position ("0", "1", …)
    minutes: int | None = None  # reading time actually spent (defaults to the item's minutes)
    notes_used: bool = False
    reference_used: bool = False
    hints_used: int = 0
    timed: bool = False
    time_seconds: int | None = None
    milestone: str | None = None  # project: the milestone being completed
    defense: bool = False  # project: the interview defense of the project
    notes: str | None = None


@dataclass(frozen=True)
class Graded:
    """The observation payload (AssessmentInput fields) plus what to show the learner."""

    payload: dict[str, Any]
    points: int | None
    passed: bool | None
    followup_points: int | None = None
    check: grading.CheckResult | None = None


class CompletionError(ValueError):
    """The submission does not fit the content item (e.g. an unknown milestone)."""


def source_key(item: ContentItem, milestone: str | None = None, defense: bool = False) -> str:
    suffix = f"#{milestone}" if milestone else "#defense" if defense else ""
    return f"{lv.SOURCE_KEY_PREFIX}{item.key}{suffix}"


def rubric_of(item: ContentItem) -> tuple[Mapping[str, Any], ...]:
    body = item.body
    if item.type == "interview_question":
        return grading.checklist_rubric(body["key_points"])
    if item.type == "behavioral_question":
        return grading.checklist_rubric(body["look_for"])
    return tuple(body.get("rubric") or ())


def grade_completion(item: ContentItem, sub: Submission, components: Mapping[str, str]) -> Graded:
    """``components``: skill key -> component (decides the project defense skills)."""
    if item.type in lv.PROBLEM_TYPES:
        raise CompletionError("guided and timed problems are recorded as problem attempts")
    base: dict[str, Any] = {"source_key": source_key(item, sub.milestone, sub.defense), "notes": sub.notes}

    if item.type in lv.READING_TYPES:
        minutes = sub.minutes if sub.minutes is not None else item.minutes
        payload = base | {
            "kind": "STUDY_SESSION",
            "study_minutes": max(1, min(minutes, 600)),
            "skills": _skills(item.skills, None),
        }
        return Graded(payload, None, None)

    if item.type in lv.CHECK_TYPES:
        if item.type == "revision_card":
            points, check = grading.grade_cards(item.body["cards"], sub.self_grades), None
        else:
            check = grading.grade_questions(item.body["questions"], sub.answers, sub.self_grades)
            points = check.points
        payload = base | {
            "kind": "RECALL_QUIZ",
            "notes_used": sub.notes_used,
            "difficulty": item.difficulty or "MEDIUM",
            "skills": _skills(item.skills, points),
        }
        return Graded(payload, points, points >= lv.CHECK_PASS_POINTS, check=check)

    if item.type == "project":
        return _project(item, sub, base, components)

    points = grading.rubric_points(rubric_of(item), sub.ratings)
    follow_ups = item.body.get("follow_ups") or ()
    fpoints = grading.followup_points(follow_ups, sub.followups) if follow_ups and sub.followups else None
    payload = (
        base
        | _practice_fields(item, sub)
        | {
            "kind": item.observation_kind,
            "followup_points": fpoints,
            "skills": _skills(item.skills, points),
        }
    )
    return Graded(payload, points, points >= lv.RUBRIC_PASS_POINTS, fpoints)


def _project(
    item: ContentItem, sub: Submission, base: dict[str, Any], components: Mapping[str, str]
) -> Graded:
    if sub.defense:
        skills = [s for s in item.skills if components.get(s) in ("project", "behavioral")]
        questions = item.body["defense_questions"]
        points = grading.share_points([(sub.ratings.get(f"q{i}", 0), 1) for i in range(len(questions))])
        payload = (
            base
            | _practice_fields(item, sub)
            | {
                "kind": lv.PROJECT_DEFENSE_KIND,
                "skills": _skills(skills, points),
            }
        )
        return Graded(payload, points, points >= lv.RUBRIC_PASS_POINTS)
    milestone = next((m for m in item.body["milestones"] if m["key"] == sub.milestone), None)
    if milestone is None:
        raise CompletionError(f"unknown milestone {sub.milestone!r}")
    points = grading.rubric_points(milestone["rubric"], sub.ratings)
    payload = (
        base
        | _practice_fields(item, sub)
        | {
            "kind": "APPLIED_TASK",
            "applied": True,
            "skills": _skills(milestone["skills"], points),
        }
    )
    return Graded(payload, points, points >= lv.RUBRIC_PASS_POINTS)


def _practice_fields(item: ContentItem, sub: Submission) -> dict[str, Any]:
    timed = bool(sub.timed and item.time_limit_seconds and sub.time_seconds is not None)
    return {
        "notes_used": sub.notes_used,
        "reference_used": sub.reference_used,
        "hints_used": max(0, min(sub.hints_used, 20)),
        "timed": timed,
        "time_limit_seconds": item.time_limit_seconds if timed else None,
        "time_seconds": sub.time_seconds if timed else None,
        "difficulty": item.difficulty or "MEDIUM",
    }


def _skills(keys: Sequence[str], points: int | None) -> list[dict[str, Any]]:
    """The first skill is the primary mapping (10000 bp); supporting skills count half (5000 bp)."""
    return [
        {"skill": k, "outcome_points": points, "mapping_weight_bp": 10000 if i == 0 else 5000}
        for i, k in enumerate(keys)
    ]
