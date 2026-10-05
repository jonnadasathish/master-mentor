"""Observation vocabulary (GLOSSARY "Outcome", EVIDENCE_MODEL §5.3, DATA_MODEL §4). Exact Spec v2 values."""

from __future__ import annotations

from typing import Final

OUTCOMES: Final = ("PASS", "PARTIAL", "FAIL")
ATTEMPT_MODES: Final = ("PRACTICE", "DIAGNOSTIC", "BASELINE", "REVISION", "SIMULATION")
MISTAKE_CODES: Final = (
    "WRONG_PATTERN",
    "NO_APPROACH",
    "MISREAD_PROBLEM",
    "EDGE_CASE_MISSED",
    "OFF_BY_ONE",
    "IMPLEMENTATION_BUG",
    "LANGUAGE_SYNTAX",
    "DATA_STRUCTURE_API",
    "WRONG_COMPLEXITY",
    "TIME_OVERRUN",
)
ASSESSMENT_KINDS: Final = (
    "STUDY_SESSION",
    "SELF_ASSESSMENT",
    "RECALL_QUIZ",
    "PATTERN_DRILL",
    "CONCEPT_EXPLAIN",
    "CODE_EXERCISE",
    "ESTIMATION_DRILL",
    "SD_DESIGN",
    "LLD_DESIGN",
    "MACHINE_CODING",
    "STORY_REHEARSAL",
    "PROJECT_WALKTHROUGH",
    "APPLIED_TASK",
)
FAMILIARITY: Final = ("NONE", "SOME", "SOLID")
UNSCORED_KINDS: Final = ("STUDY_SESSION", "SELF_ASSESSMENT")  # L0: no outcome points (EVIDENCE_MODEL §5.4)
ANY_COMPONENT: Final = ("dsa", "coding", "cs", "lld", "system_design", "behavioral", "project")
# Skill components an assessment kind may observe (API_SPEC "allowed components"; D-055).
ASSESSMENT_COMPONENTS: Final[dict[str, tuple[str, ...]]] = {
    "STUDY_SESSION": ANY_COMPONENT,
    "SELF_ASSESSMENT": ANY_COMPONENT,
    "RECALL_QUIZ": ANY_COMPONENT,
    "CONCEPT_EXPLAIN": ANY_COMPONENT,
    "APPLIED_TASK": ANY_COMPONENT,
    "PATTERN_DRILL": ("dsa",),
    "CODE_EXERCISE": ("coding", "dsa"),
    "ESTIMATION_DRILL": ("system_design",),
    "SD_DESIGN": ("system_design", "cs"),
    "LLD_DESIGN": ("lld", "coding"),
    "MACHINE_CODING": ("lld", "coding"),
    "STORY_REHEARSAL": ("behavioral",),
    "PROJECT_WALKTHROUGH": ("project", "behavioral"),
}
MAX_ASSESSMENT_SKILLS: Final = 20
MAX_SWEEP_SKILLS: Final = 200
DIFFICULTIES: Final = ("EASY", "MEDIUM", "HARD")
MAX_STUDY_MINUTES: Final = 600
EXECUTION_RUBRIC_DIMENSIONS: Final = (
    "clarification",
    "think_aloud",
    "testing",
    "time_management",
    "optimization",
)

SELF_RATING_MIN: Final = 1
SELF_RATING_MAX: Final = 5
SCORE_10_MIN: Final = 0  # explanation_score and execution rubric dimensions
SCORE_10_MAX: Final = 10
MAX_HINTS: Final = 20
MAX_SECONDS: Final = 6 * 3600  # one attempt never exceeds 6 hours
MIN_TIME_LIMIT_SECONDS: Final = 60
MAX_NOTES_CHARS: Final = 4000
MAX_MISTAKES: Final = len(MISTAKE_CODES)
FUTURE_TOLERANCE_SECONDS: Final = 300  # clock skew allowance for attempted_at

# Personal problems live above the seed id range so a future seed can never collide (D-050).
PERSONAL_PROBLEM_ID_START: Final = 1_000_000
PERSONAL_SEED_VERSION: Final = "user"
