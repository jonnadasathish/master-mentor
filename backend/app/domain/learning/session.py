"""Learning sessions (LEARNING_ENGINE §5): a mentor stage expanded into concrete steps. Pure and
deterministic.

The mentor decides the skill and the stage (unchanged engines). This module only decides *which content* fills
that stage, in a fixed slot order, preferring items made for the stage, then items not done yet, then
seed order.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from app.domain.communication.cross_track import ExplainCandidate
from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem

PRACTICE_TYPES = (
    "coding_exercise",
    "sql_exercise",
    "debugging_exercise",
    "design_exercise",
    "architecture_case",
    "behavioral_question",
    "interview_question",
)

# Slot = (content types in preference order, problem allowed in this slot, problem difficulty).
_Slot = tuple[tuple[str, ...], bool, str | None]
SLOTS: dict[str, tuple[_Slot, ...]] = {
    "LEARN": (
        (("lesson", "concept"), False, None),
        (("worked_example", "visual_explanation"), False, None),
        (("concept_check", "quiz"), False, None),
        (("guided_problem", *PRACTICE_TYPES), True, "EASY"),
    ),
    "DIAGNOSE": (
        (("concept_check", "quiz"), False, None),
        ((*PRACTICE_TYPES, "timed_problem"), True, "MEDIUM"),
    ),
    "RECALL": ((("revision_card",), False, None), (("concept_check", "quiz"), False, None)),
    "REINFORCE": (
        (("revision_card", "lesson", "concept"), False, None),
        (("concept_check", "quiz"), False, None),
        ((*PRACTICE_TYPES, "guided_problem"), True, "MEDIUM"),
    ),
    "REVISION": (
        (("revision_card",), False, None),
        (("concept_check", "quiz", "interview_question"), False, None),
    ),
    "GUIDED": (
        (("worked_example", "visual_explanation"), False, None),
        (("guided_problem", *PRACTICE_TYPES), True, "EASY"),
    ),
    "INDEPENDENT": ((PRACTICE_TYPES, True, "MEDIUM"),),
    "TIMED": ((("timed_problem", *PRACTICE_TYPES), True, "MEDIUM"),),
    "EXPLAIN": (
        (("interview_question",), False, None),
        (("interview_question", "behavioral_question"), False, None),
    ),
    "THINK_ALOUD": ((("interview_question", "behavioral_question"), True, "MEDIUM"),),
    "TRANSFER": (
        (("project", "architecture_case", "design_exercise", "debugging_exercise"), True, "HARD"),
        (("interview_question",), False, None),
    ),
    "SIMULATE": (
        (
            ("architecture_case", "design_exercise", "interview_question", "behavioral_question"),
            True,
            "MEDIUM",
        ),
    ),
    "PATTERN_DRILL": ((("concept_check", "quiz"), True, "MEDIUM"),),
}
WITH_REFLECTION = (
    "LEARN",
    "GUIDED",
    "INDEPENDENT",
    "TIMED",
    "EXPLAIN",
    "THINK_ALOUD",
    "TRANSFER",
    "SIMULATE",
)


@dataclass(frozen=True)
class ProblemOption:
    id: int
    title: str
    difficulty: str
    expected_minutes: int


@dataclass(frozen=True)
class Step:
    position: int
    kind: str  # CONTENT | PROBLEM | REFLECTION
    minutes: int
    content_key: str | None = None
    content_type: str | None = None
    problem_id: int | None = None
    title: str = ""
    optional: bool = False  # D-087: cross-track communication prompt


def compose_session(
    *,
    stage: str,
    content: Sequence[ContentItem],
    problems: Sequence[ProblemOption],
    done: Collection[str],
    attempted: Collection[int],
    budget_minutes: int | None,
    explain: ExplainCandidate | None = None,
) -> tuple[Step, ...]:
    """``content``: the items mapped to the skill (``LearningCatalog.for_skill`` order). ``done``:
    content keys
    already completed; ``attempted``: problem ids already attempted. A step never repeats an item."""
    slots = SLOTS.get(stage, SLOTS["LEARN"])
    used: set[str] = set()
    used_problems: set[int] = set()
    chosen: list[tuple[str, int, str | None, str | None, int | None, str]] = []
    timed = stage == "TIMED"
    for types, allow_problem, difficulty in slots:
        item = _pick(content, types, stage, done, used, timed)
        if item is not None:
            used.add(item.key)
            chosen.append(("CONTENT", item.minutes, item.key, item.type, None, item.title))
            continue
        if allow_problem:
            problem = _pick_problem(problems, difficulty, attempted, used_problems)
            if problem is not None:
                used_problems.add(problem.id)
                chosen.append(("PROBLEM", problem.expected_minutes, None, None, problem.id, problem.title))
    if not chosen:
        return ()
    steps: list[Step] = []
    total = 0
    for kind, minutes, key, ctype, pid, title in chosen:
        if steps and budget_minutes is not None and total + minutes > budget_minutes:
            continue  # later, smaller steps may still fit; order is preserved
        steps.append(Step(len(steps) + 1, kind, minutes, key, ctype, pid, title))
        total += minutes
        if len(steps) == lv.MAX_SESSION_STEPS - 1:
            break
    # D-087: one optional "explain it aloud" step, only when it fits the budget and the step cap.
    if (
        explain is not None
        and len(steps) < lv.MAX_SESSION_STEPS - 1
        and (budget_minutes is None or total + explain.minutes <= budget_minutes)
    ):
        steps.append(
            Step(
                len(steps) + 1,
                "CONTENT",
                explain.minutes,
                explain.key,
                "interview_question",
                None,
                explain.title,
                optional=True,
            )
        )
        total += explain.minutes
    room = budget_minutes is None or total + lv.REFLECTION_MINUTES <= budget_minutes
    if stage in WITH_REFLECTION and room:
        steps.append(Step(len(steps) + 1, "REFLECTION", lv.REFLECTION_MINUTES, title="Reflection"))
    return tuple(steps)


def _pick(
    content: Sequence[ContentItem],
    types: Sequence[str],
    stage: str,
    done: Collection[str],
    used: Collection[str],
    timed: bool,
) -> ContentItem | None:
    # ``content`` arrives primary-skill items first (LearningCatalog.for_skill): keep that order as the last
    # tiebreaker so a skill's own lesson beats a lesson that only lists it as a supporting skill.
    order = {c.key: i for i, c in enumerate(content)}
    candidates = [c for c in content if c.type in types and c.key not in used]
    if timed:
        candidates = [c for c in candidates if c.type == "timed_problem" or c.time_limit_seconds]
    if not candidates:
        return None

    def rank(c: ContentItem) -> tuple[int, int, int, int]:
        return (int(stage not in c.stages), int(c.key in done), types.index(c.type), order[c.key])

    return min(candidates, key=rank)


def _pick_problem(
    problems: Sequence[ProblemOption],
    difficulty: str | None,
    attempted: Collection[int],
    used: Collection[int],
) -> ProblemOption | None:
    order = {"EASY": 0, "MEDIUM": 1, "HARD": 2}
    candidates = [p for p in problems if p.id not in used]
    if not candidates:
        return None
    wanted = order.get(difficulty or "MEDIUM", 1)

    def rank(p: ProblemOption) -> tuple[int, int, int]:
        return (int(p.id in attempted), abs(order.get(p.difficulty, 1) - wanted), p.id)

    return min(candidates, key=rank)


# ------------------------------------------------------------------------------------------------ state


@dataclass(frozen=True)
class StepState:
    position: int
    status: str  # PENDING | DONE | SKIPPED
    points: int | None
    passed: bool | None


@dataclass(frozen=True)
class SessionSummary:
    status: str  # ACTIVE | COMPLETED
    done: int
    skipped: int
    pending: int
    scored: int
    passed: int
    outcome: str | None  # PASSED | NEEDS_REPEAT | NOT_SCORED (only when COMPLETED)
    next_position: int | None


def summarize(steps: Sequence[StepState]) -> SessionSummary:
    pending = [s for s in steps if s.status == "PENDING"]
    done = [s for s in steps if s.status == "DONE"]
    scored = [s for s in done if s.passed is not None]
    passed = [s for s in scored if s.passed]
    if pending:
        return SessionSummary(
            "ACTIVE",
            len(done),
            len(steps) - len(done) - len(pending),
            len(pending),
            len(scored),
            len(passed),
            None,
            min(s.position for s in pending),
        )
    outcome = "NOT_SCORED" if not scored else "PASSED" if len(passed) == len(scored) else "NEEDS_REPEAT"
    return SessionSummary(
        "COMPLETED", len(done), len(steps) - len(done), 0, len(scored), len(passed), outcome, None
    )


def done_content(observed: Mapping[str, Sequence[bool | None]]) -> frozenset[str]:
    """Content keys with at least one completion (``observed``: content key -> passed flags, None =
    unscored)."""
    return frozenset(k for k, flags in observed.items() if flags)
