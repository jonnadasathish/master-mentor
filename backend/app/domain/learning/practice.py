"""Practice resolution for a skill (the dead-end rule, MASTER_SPEC_V3 §8) and derived per-problem
practice state.

Resolution never returns "nothing": a skill with no direct problem and no content still gets the nearest
prerequisite or same-group skill that has practice, and is reported as UNCOVERED so the gap stays visible.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem

MAX_RELATED = 6
DIFFICULTY_ORDER = {"EASY": 0, "MEDIUM": 1, "HARD": 2}


@dataclass(frozen=True)
class ProblemRef:
    id: int
    title: str
    difficulty: str
    canonical: bool
    weight_bp: int  # mapping weight to the skill it was found through


@dataclass(frozen=True)
class RelatedProblem:
    problem: ProblemRef
    via_skill: str
    relation: str  # USES_THIS (a dependent skill) | FOUNDATION (a prerequisite) | SAME_GROUP


@dataclass(frozen=True)
class PracticeResolution:
    case: str  # DIRECT | RELATED | CONCEPT | UNCOVERED
    direct: tuple[ProblemRef, ...]
    related: tuple[RelatedProblem, ...]
    content: tuple[str, ...]  # practice + test content keys for this skill
    fallback_skill: str | None  # UNCOVERED: nearest skill that has practice
    fallback_relation: str | None  # FOUNDATION | SAME_GROUP


def _ordered(problems: Sequence[ProblemRef]) -> tuple[ProblemRef, ...]:
    """Primary mappings first, then easiest first (a learner climbs), canonical before others, then id."""
    return tuple(
        sorted(
            problems,
            key=lambda p: (-p.weight_bp, DIFFICULTY_ORDER.get(p.difficulty, 1), not p.canonical, p.id),
        )
    )


def resolve_practice(
    *,
    skill: str,
    component: str,
    prerequisites: Sequence[str],
    dependents: Sequence[str],
    group_skills: Sequence[str],
    problems_by_skill: Mapping[str, Sequence[ProblemRef]],
    content_by_skill: Mapping[str, Sequence[ContentItem]],
) -> PracticeResolution:
    def practice_content(key: str) -> tuple[str, ...]:
        return tuple(
            c.key for c in content_by_skill.get(key, ()) if lv.TAB_OF_TYPE[c.type] in ("practice", "test")
        )

    own_content = practice_content(skill)
    direct = _ordered(problems_by_skill.get(skill, ()))
    related: list[RelatedProblem] = []
    if component in lv.PROBLEM_COMPONENTS and not direct:
        seen: set[int] = set()
        for relation, keys in (
            ("USES_THIS", dependents),
            ("FOUNDATION", prerequisites),
            ("SAME_GROUP", group_skills),
        ):
            for key in keys:
                if key == skill:
                    continue
                for p in _ordered(problems_by_skill.get(key, ())):
                    if p.id not in seen and len(related) < MAX_RELATED:
                        seen.add(p.id)
                        related.append(RelatedProblem(p, key, relation))
    if direct:
        case = "DIRECT"
    elif own_content:
        case = "CONCEPT"
    elif related:
        case = "RELATED"
    else:
        case = "UNCOVERED"
    fallback, fallback_relation = None, None
    if case == "UNCOVERED":
        for relation, keys in (("FOUNDATION", prerequisites), ("SAME_GROUP", group_skills)):
            hit = next(
                (k for k in keys if k != skill and (practice_content(k) or problems_by_skill.get(k))), None
            )
            if hit is not None:
                fallback, fallback_relation = hit, relation
                break
    return PracticeResolution(case, direct, tuple(related), own_content, fallback, fallback_relation)


# ------------------------------------------------------------------------------------- problem practice state


@dataclass(frozen=True)
class AttemptFact:
    outcome: str  # PASS | PARTIAL | FAIL
    hints_used: int
    solution_viewed: bool
    timed: bool
    within_limit: bool
    explanation_score: int | None
    complexity_correct: bool | None


def _strength(a: AttemptFact) -> str:
    if a.outcome == "PASS" and not a.solution_viewed:
        if a.hints_used > 0:
            return "solved_with_hint"
        if a.timed and a.within_limit:
            explained = (
                a.explanation_score or 0
            ) >= lv.INTERVIEW_GRADE_EXPLANATION and a.complexity_correct is True
            return "interview_grade" if explained else "timed_solve"
        return "independent_solve"
    if a.solution_viewed and a.outcome in ("PASS", "PARTIAL"):
        return "solved_after_solution"
    if a.outcome == "FAIL":
        return "failed"
    return "attempted"


def problem_state(attempts: Sequence[AttemptFact]) -> str:
    """The strongest state any current attempt reached (completion is not mastery: the states are ordered)."""
    if not attempts:
        return "not_started"
    return max((_strength(a) for a in attempts), key=lv.PROBLEM_STATES.index)
