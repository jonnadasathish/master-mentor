"""Learning-layer vocabulary (docs/domain/LEARNING_ENGINE.md). Content produces existing observation
kinds only."""

from __future__ import annotations

import re
from typing import Final

CONTENT_TYPES: Final = (
    "lesson",
    "concept",
    "worked_example",
    "visual_explanation",
    "concept_check",
    "quiz",
    "coding_exercise",
    "guided_problem",
    "timed_problem",
    "debugging_exercise",
    "sql_exercise",
    "design_exercise",
    "architecture_case",
    "project",
    "interview_question",
    "behavioral_question",
    "revision_card",
)

# Content read for understanding: completion records a STUDY_SESSION (L0, minutes, never a score).
READING_TYPES: Final = ("lesson", "concept", "worked_example", "visual_explanation")
# Closed-book checks graded by the server: completion records a RECALL_QUIZ (L1 closed-book, L0 with notes).
CHECK_TYPES: Final = ("concept_check", "quiz", "revision_card")
# Practice scored with a rubric (outcome_points) and an optional follow-up rubric (followup_points).
RUBRIC_TYPES: Final = (
    "coding_exercise",
    "debugging_exercise",
    "sql_exercise",
    "design_exercise",
    "architecture_case",
    "interview_question",
    "behavioral_question",
)
# Practice on a seeded problem: completion is an ordinary problem attempt (EVIDENCE_MODEL §5.1).
PROBLEM_TYPES: Final = ("guided_problem", "timed_problem")
PROJECT_TYPES: Final = ("project",)

# Observation kind each type may declare (the first is the default). Skill components are checked against
# activity.vocabulary.ASSESSMENT_COMPONENTS by the validator, so a recorded completion never fails validation.
TYPE_KINDS: Final[dict[str, tuple[str, ...]]] = {
    "lesson": ("STUDY_SESSION",),
    "concept": ("STUDY_SESSION",),
    "worked_example": ("STUDY_SESSION",),
    "visual_explanation": ("STUDY_SESSION",),
    "concept_check": ("RECALL_QUIZ",),
    "quiz": ("RECALL_QUIZ",),
    "revision_card": ("RECALL_QUIZ",),
    "coding_exercise": ("CODE_EXERCISE", "CONCEPT_EXPLAIN"),
    "debugging_exercise": ("CONCEPT_EXPLAIN", "CODE_EXERCISE"),
    "sql_exercise": ("CONCEPT_EXPLAIN",),
    "design_exercise": ("LLD_DESIGN", "MACHINE_CODING"),
    "architecture_case": ("SD_DESIGN", "ESTIMATION_DRILL"),
    "interview_question": ("CONCEPT_EXPLAIN",),
    "behavioral_question": ("STORY_REHEARSAL",),
    "guided_problem": ("ATTEMPT",),
    "timed_problem": ("ATTEMPT",),
    "project": ("APPLIED_TASK",),  # per milestone; the defense records PROJECT_WALKTHROUGH
}
PROJECT_DEFENSE_KIND: Final = "PROJECT_WALKTHROUGH"

# Where a type appears on the skill page.
TAB_OF_TYPE: Final[dict[str, str]] = {
    "lesson": "learn",
    "concept": "learn",
    "worked_example": "learn",
    "visual_explanation": "learn",
    "concept_check": "test",
    "quiz": "test",
    "interview_question": "test",
    "behavioral_question": "practice",
    "coding_exercise": "practice",
    "debugging_exercise": "practice",
    "sql_exercise": "practice",
    "design_exercise": "practice",
    "architecture_case": "practice",
    "guided_problem": "practice",
    "timed_problem": "practice",
    "project": "practice",
    "revision_card": "revision",
}
TABS: Final = ("learn", "practice", "test", "revision")

DIFFICULTIES: Final = ("EASY", "MEDIUM", "HARD")
QUESTION_KINDS: Final = ("single", "multi", "short")
RATINGS: Final = (0, 1, 2)  # missed / partly / fully (rubric criteria, follow-ups, self-graded short answers)
MIN_QUESTIONS: Final[dict[str, int]] = {"concept_check": 3, "quiz": 5}
MIN_CARDS: Final = 3
CHECK_PASS_POINTS: Final = 60  # same bar as the recall templates (MISSION_LIBRARY: outcome_points >= 60)
RUBRIC_PASS_POINTS: Final = 70  # same bar as the practice templates (outcome_points >= 70)
MAX_RUBRIC_POINTS: Final = 10
MAX_CONTENT_MINUTES: Final = 180
MAX_TIME_LIMIT_SECONDS: Final = 5400
CONTENT_KEY_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
MAX_CONTENT_KEY_LENGTH: Final = 80  # source_key "content:<key>" must fit 96 characters
SOURCE_KEY_PREFIX: Final = "content:"
TRACK_KEY_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")

# Learning sessions (user state).
SESSION_STATUSES: Final = ("ACTIVE", "COMPLETED", "ABANDONED")
STEP_STATUSES: Final = ("PENDING", "DONE", "SKIPPED")
STEP_KINDS: Final = ("CONTENT", "PROBLEM", "REFLECTION")
REFLECTION_MINUTES: Final = 3
MAX_SESSION_STEPS: Final = 7

# Coverage report (LEARNING_ENGINE §8).
COVERAGE_STATES: Final = ("FULL", "PARTIAL", "UNMEASURED", "CONTENT_GAP")

# Practice resolution on a skill page (MASTER_SPEC_V3 §8).
PRACTICE_CASES: Final = ("DIRECT", "RELATED", "CONCEPT", "UNCOVERED")
PROBLEM_COMPONENTS: Final = ("dsa", "coding")

# Derived practice state of one problem (MASTER_SPEC_V3 §9, §11), weakest to strongest.
PROBLEM_STATES: Final = (
    "not_started",
    "attempted",
    "failed",
    "solved_after_solution",
    "solved_with_hint",
    "independent_solve",
    "timed_solve",
    "interview_grade",
)
INTERVIEW_GRADE_EXPLANATION: Final = 7  # EVIDENCE_MODEL §3 L5: explanation >= 7/10 and correct complexity
