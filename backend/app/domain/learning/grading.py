"""Deterministic grading of learning content (LEARNING_ENGINE §4). Integers + Decimal, one ROUND_HALF_UP.

Every gradable unit earns 0, 1 or 2 halves: a choice question is right (2) or wrong (0); a self-graded
short answer, recall card, rubric criterion or follow-up is missed (0), partly (1) or fully (2) there.
Points are the weighted share of halves earned, as an integer 0-100.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

FULL = 2


@dataclass(frozen=True)
class QuestionResult:
    id: str
    kind: str
    earned: int  # 0..2 halves
    chosen: tuple[int, ...]
    answer: tuple[int, ...]  # the correct option indexes (empty for short answers)
    explanation: str
    model_answer: str | None


@dataclass(frozen=True)
class CheckResult:
    points: int
    questions: tuple[QuestionResult, ...]


def share_points(earned: Sequence[tuple[int, int]]) -> int:
    """``earned``: (halves 0..2, weight >= 1) per unit -> integer points 0-100 (ROUND_HALF_UP)."""
    total = sum(weight * FULL for _, weight in earned)
    if total == 0:
        return 0
    got = sum(min(max(halves, 0), FULL) * weight for halves, weight in earned)
    return int((Decimal(got) * 100 / Decimal(total)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def grade_questions(
    questions: Sequence[Mapping[str, Any]],
    answers: Mapping[str, Sequence[int]],
    self_grades: Mapping[str, int],
) -> CheckResult:
    """Choice questions are graded against the answer key; short answers use the learner's own grade
    against the model answer. A question without an answer earns 0."""
    results: list[QuestionResult] = []
    for q in questions:
        qid, kind = str(q["id"]), str(q["kind"])
        if kind == "short":
            earned = rating_of(self_grades.get(qid))
            results.append(
                QuestionResult(qid, kind, earned, (), (), str(q["explanation"]), str(q["model_answer"]))
            )
            continue
        key = tuple(sorted(int(a) for a in q["answer"]))
        chosen = tuple(sorted({int(a) for a in answers.get(qid, ())}))
        earned = FULL if chosen == key else 0
        results.append(QuestionResult(qid, kind, earned, chosen, key, str(q["explanation"]), None))
    return CheckResult(share_points([(r.earned, 1) for r in results]), tuple(results))


def grade_cards(cards: Sequence[Mapping[str, Any]], grades: Mapping[str, int]) -> int:
    """Recall cards are keyed by position ("0", "1", ...)."""
    return share_points([(rating_of(grades.get(str(i))), 1) for i in range(len(cards))])


def rubric_points(rubric: Sequence[Mapping[str, Any]], ratings: Mapping[str, int]) -> int:
    return share_points([(rating_of(ratings.get(str(r["key"]))), int(r["points"])) for r in rubric])


def followup_points(follow_ups: Sequence[Mapping[str, Any]], ratings: Mapping[str, int]) -> int:
    """Follow-ups are keyed by position ("0", "1", ...)."""
    return share_points([(rating_of(ratings.get(str(i))), 1) for i in range(len(follow_ups))])


def checklist_rubric(points: Sequence[str]) -> tuple[dict[str, Any], ...]:
    """Interview and behavioral questions are scored on their key points / what good looks like (1
    point each)."""
    return tuple({"key": f"p{i}", "label": text, "points": 1} for i, text in enumerate(points))


def rating_of(value: int | None) -> int:
    return value if value in (0, 1, 2) else 0
