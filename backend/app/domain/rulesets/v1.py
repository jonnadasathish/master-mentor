"""Ruleset v1: every formula / rule constant of Specification v2.

Rules:
- This module is FROZEN. Changing any value here requires a new module (v2.py), a new entry in
  ``app.domain.rulesets.RULESETS``, a frozen fingerprint in ``fingerprints.py``, a DECISION_LOG entry,
  and recomputed SCENARIOS.md numbers (CLAUDE.md rule 12). ``tests/unit/test_ruleset_version.py`` enforces it.
- Integers only (scores, points, minutes, basis points, days). Ratios are (numerator, denominator) tuples.
- Benchmark parameters (component weights, gates, tiers, track minutes, weekday budgets) are NOT here:
  they are role-profile data versioned by ``seed_version`` (seed/role_profiles/*.yaml, D-002/D-003).

Section references point to the owning document in docs/domain/.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

RULESET_VERSION: Final = "v1"

# ---------------------------------------------------------------------------------------------------
# EVIDENCE_MODEL.md
# ---------------------------------------------------------------------------------------------------

# §3 / §7.3 — level bands (lo, hi) for L0..L7
LEVEL_BANDS: Final = MappingProxyType(
    {0: (0, 10), 1: (10, 30), 2: (30, 45), 3: (45, 60), 4: (60, 72), 5: (72, 82), 6: (82, 90), 7: (90, 100)}
)

# §4 — outcome points for problem attempts (first match wins, in this order)
OUTCOME_POINTS: Final = MappingProxyType(
    {
        "FAIL": 0,
        "SOLUTION_VIEWED": 20,
        "PARTIAL": 50,
        "PASS_2_PLUS_HINTS": 60,
        "PASS_1_HINT": 80,
        "PASS_NO_HINTS": 100,
    }
)
SELF_MOCK_OUTCOME_CAP: Final = 80

# §5.1 — attempt level derivation
L5_MIN_EXPLANATION_SCORE: Final = 7  # of 10
EASY_LEVEL_CAP: Final = 3
SEEN_PROBLEM_LEVEL_CAP: Final = 3
SEEN_RECENT_LEVEL_CAP: Final = 1
SEEN_RECENT_DAYS: Final = 7
DEFAULT_EXPECTED_MINUTES: Final = MappingProxyType({"EASY": 15, "MEDIUM": 30, "HARD": 45})

# §5.3 — mistake routing (negative evidence) and bug-class mistakes
MISTAKE_ROUTING: Final = MappingProxyType(
    {
        "WRONG_PATTERN": ("dsa.pattern_recognition",),
        "NO_APPROACH": (),
        "MISREAD_PROBLEM": ("execution.clarification",),
        "EDGE_CASE_MISSED": ("execution.testing_dry_run",),
        "OFF_BY_ONE": ("execution.bug_free_coding",),
        "IMPLEMENTATION_BUG": ("execution.bug_free_coding",),
        "LANGUAGE_SYNTAX": ("python.core_syntax",),
        "DATA_STRUCTURE_API": ("python.collections",),
        "WRONG_COMPLEXITY": ("dsa.complexity_analysis", "execution.brute_force_to_optimal"),
        "TIME_OVERRUN": ("execution.time_management",),
    }
)
BUG_CLASS_MISTAKES: Final = ("DATA_STRUCTURE_API", "IMPLEMENTATION_BUG", "LANGUAGE_SYNTAX", "OFF_BY_ONE")
EXECUTION_RUBRIC_SKILLS: Final = MappingProxyType(
    {
        "clarification": "execution.clarification",
        "think_aloud": "execution.think_aloud",
        "testing": "execution.testing_dry_run",
        "time_management": "execution.time_management",
        "optimization": "execution.brute_force_to_optimal",
    }
)

# §5.4 — assessments
FOLLOWUP_MIN_POINTS: Final = 70
PATTERN_DRILL_STATEMENTS: Final = 5
PATTERN_DRILL_POINTS_PER_CORRECT: Final = 20

# §6 — weights (basis points)
RECENCY_BP: Final = ((30, 10000), (60, 8500), (90, 7000), (120, 5500))  # (max age days, bp)
RECENCY_BP_OLDER: Final = 3000
DIFFICULTY_BP: Final = MappingProxyType({"EASY": 8000, "MEDIUM": 10000, "HARD": 12000})
MAPPING_BP_PRIMARY: Final = 10000
MAPPING_BP_SECONDARY: Final = 5000
MAPPING_BP_DERIVED: Final = 10000

# §7.1 — level qualification: level -> (rows needed, distinct source keys, min outcome points)
QUALIFICATION: Final = MappingProxyType(
    {1: (1, 1, 60), 2: (2, 2, 60), 3: (2, 2, 70), 4: (2, 2, 70), 5: (2, 2, 70), 6: (2, 2, 70), 7: (2, 2, 75)}
)
LEVEL_WINDOW_DAYS: Final = 120  # L1 has no age window
QUALITY_FAILURE_BELOW_POINTS: Final = 60  # §7.2 recent failures at any level are always considered

# §7.3 — interview reality cap
REALITY_CAP_WINDOW_DAYS: Final = 60
REALITY_CAP_BELOW_POINTS: Final = 70

# §8 — confidence
CONFIDENCE_WINDOW_DAYS: Final = 120
CONFIDENCE_MEDIUM: Final = MappingProxyType({"min_rows": 3, "min_distinct": 2})
CONFIDENCE_HIGH: Final = MappingProxyType(
    {"min_rows": 6, "min_distinct": 3, "recent_days": 30, "min_levels": 2}
)

# §9 — effective score uncertainty penalty
UNCERTAINTY: Final = MappingProxyType({"LOW": 15, "MEDIUM": 7, "HIGH": 0})

# §10 — display labels on effective score: (label, min inclusive), checked top-down
SKILL_LABELS: Final = (
    ("INTERVIEW_GRADE", 82),
    ("STRONG", 72),
    ("WORKING", 60),
    ("DEVELOPING", 45),
    ("WEAK", 0),
)

# ---------------------------------------------------------------------------------------------------
# GAP_ENGINE.md
# ---------------------------------------------------------------------------------------------------

# §2 — prep phases (weeks_left = days / 7)
PHASE_BUILD_ABOVE_WEEKS: Final = 12
PHASE_SHARPEN_AT_OR_BELOW_WEEKS: Final = 4

# §4 — assessment priority
ASSESS_DOWNSTREAM_BONUS: Final = 10
ASSESS_DOWNSTREAM_MAX: Final = 5

# §5 — pressure (basis points)
PRESSURE_BASE_BP: Final = 10000
PRESSURE_CAP_BP: Final = 17000
FAILURE_BP_PER_FAIL: Final = 800
FAILURE_WINDOW_ROWS: Final = 5
FAILURE_MIN_COUNT: Final = 2
FAILURE_MAX_COUNTED: Final = 3
FAILURE_BELOW_POINTS: Final = 60
MOCK_BP: Final = 1500
MOCK_WINDOW_ROUNDS: Final = 3
MOCK_WINDOW_DAYS: Final = 60
GATE_BP: Final = 2000
FLOOR_BP: Final = 1500
RETENTION_BP: Final = 1000
RETENTION_PRESSURE_DAYS: Final = 45
RETENTION_PRESSURE_MIN_IMPORTANCE: Final = 75

# §6 — gap-type thresholds
GAP_TYPE_ORDER: Final = (
    "UNASSESSED",
    "PREREQUISITE",
    "KNOWLEDGE",
    "RETENTION",
    "PATTERN_RECOGNITION",
    "PRACTICE",
    "CONFIDENCE",
    "SPEED",
    "DEPTH",
    "COMMUNICATION",
    "INTERVIEW_EXECUTION",
    "EXPERIENCE",
    "LEVEL_UP",
)
COMMUNICATION_SKILLS: Final = (
    "communication.followup_handling",
    "communication.structured_answers",
    "execution.clarification",
    "execution.think_aloud",
)
KNOWLEDGE_L1_ROWS: Final = 2
KNOWLEDGE_L1_BELOW_POINTS: Final = 60
RETENTION_PEAK_DROP: Final = 15
RETENTION_MIN_DAYS: Final = 21
RETENTION_MIN_LAPSES: Final = 2
PATTERN_WINDOW_ATTEMPTS: Final = 4
PATTERN_MIN_MISSES: Final = 2
CONFIDENCE_GAP_WINDOW_ROWS: Final = 10
OVERCONFIDENT_MIN_RATING: Final = 4
OVERCONFIDENT_BELOW_POINTS: Final = 50
OVERCONFIDENT_MIN_COUNT: Final = 3
UNDERCONFIDENT_MAX_RATING: Final = 2
UNDERCONFIDENT_MIN_POINTS: Final = 80
UNDERCONFIDENT_MIN_COUNT: Final = 3
SPEED_WINDOW_ROWS: Final = 3
SPEED_RATIO_BP: Final = 12500
SPEED_MIN_POINTS: Final = 70
SPEED_OVER_LIMIT_MIN_COUNT: Final = 2
DEPTH_WINDOW_ROWS: Final = 3
DEPTH_BELOW_POINTS: Final = 60
COMMUNICATION_WINDOW_ROWS: Final = 3
COMMUNICATION_BELOW_POINTS: Final = 60
COMMUNICATION_MIN_OUTCOME: Final = 70
COMMUNICATION_SKILL_MIN_ROWS: Final = 3
INTERVIEW_EXECUTION_BELOW_POINTS: Final = 60
INTERVIEW_EXECUTION_WINDOW_DAYS: Final = 60
EXPERIENCE_COMPONENTS: Final = ("lld", "project", "system_design")
LEVEL_UP_STAGE: Final = MappingProxyType(
    {
        0: "LEARN",
        1: "GUIDED",
        2: "INDEPENDENT",
        3: "TIMED",
        4: "EXPLAIN",
        5: "TRANSFER",
        6: "SIMULATE",
        7: "SIMULATE",
    }
)

# §7 — status thresholds (absolute; never normalized)
STATUS_THRESHOLDS: Final = (("CRITICAL", 60), ("HIGH", 40), ("MEDIUM", 25), ("LOW", 10))
UNLOCK_SHARE: Final = (90, 100)

# §8 — parking and feasibility
FEASIBILITY_MIN_ASSESSED_PCT: Final = 60
MIN_PER_POINT: Final = MappingProxyType(
    {"dsa": 6, "coding": 2, "cs": 3, "lld": 5, "system_design": 4, "behavioral": 2, "project": 2}
)

# §9 — reason-code thresholds
LARGE_GAP_MIN: Final = 30
HIGH_IMPORTANCE_MIN: Final = 75
STUDIED_NOT_TESTED_DAYS: Final = 14

# ---------------------------------------------------------------------------------------------------
# REVISION_ENGINE.md
# ---------------------------------------------------------------------------------------------------

STANDARD_INTERVALS: Final = (1, 3, 7, 14, 30, 60)
MOCKW_INTERVALS: Final = (2, 5, 12)
INITIAL_INDEX: Final = MappingProxyType(
    {"below_50": 0, "50_to_89_or_slow": 1, "90_plus": 2, "PATTERN": 1, "BEHAVIORAL": 0}
)
INITIAL_INDEX_SLOW_RATIO_BP: Final = 12500
REVIEW_PASS_MIN_POINTS: Final = 70
REVIEW_PARTIAL_MIN_POINTS: Final = 50
LEECH_LAPSES: Final = 3
REACTIVATION_MIN_LEVEL: Final = 2
REACTIVATION_MIN_POINTS: Final = 70
MAINTENANCE_DAYS: Final = 120
MAINTENANCE_PARTIAL_DAYS: Final = 60
MAINTENANCE_FAIL_INDEX: Final = 2
MAINTENANCE_FAIL_DUE_DAYS: Final = 7
REVISION_CAP_PCT: Final = 40
REVISION_CAP_MIN_MINUTES: Final = 15
TRIAGE_TRIGGER_MULTIPLE: Final = 14
TRIAGE_TARGET_MULTIPLE: Final = 7
RESUME_BELOW_MULTIPLE: Final = 3
RESUME_MAX_PER_DAY: Final = 3
REINFORCE_EXTRA_MINUTES: Final = 10
MOCKW_MAX_PER_ROUND: Final = 3
REVISION_ITEM_MINUTES: Final = MappingProxyType(
    {
        "PROBLEM_EASY": 15,
        "PROBLEM_MEDIUM": 25,
        "PROBLEM_HARD": 35,
        "PATTERN": 10,
        "CS": 10,
        "CONCEPT": 10,
        "SD": 20,
        "STORY": 10,
        "PROJECT": 15,
        "MOCK_WEAKNESS": 15,
    }
)
G7_OVERDUE_DAYS: Final = 7  # also a role-profile gate parameter; used here for revision_health()

# ---------------------------------------------------------------------------------------------------
# MENTOR_ENGINE.md
# ---------------------------------------------------------------------------------------------------

CALIBRATION_MIN_ASSESSED_PCT: Final = 60
CALIBRATION_DIAGNOSTIC_BUDGET_PCT: Final = 60
DIAGNOSTIC_FACTOR: Final = (70, 100)
REVISION_SCORE_OVERDUE_BASE: Final = 60
REVISION_SCORE_OVERDUE_MAX_DAYS: Final = 20
REVISION_SCORE_DUE_BASE: Final = 50
REVISION_SCORE_MAINTENANCE_BASE: Final = 30
REVISION_SCORE_IMPORTANCE_DIVISOR: Final = 5
REVISION_SCORE_CAP: Final = 100
CONTINUATION_BONUS: Final = 10
CONTINUATION_WINDOW_DAYS: Final = 3
MAINTENANCE_SCORE: Final = 20
MAINTENANCE_MIN_DAYS_SINCE_PRACTICE: Final = 21
MOCK_SCORE: Final = 55
MOCK_SPACING_DAYS: Final = 7
MOCK_SPACING_DAYS_SHARPEN: Final = 3
FINAL_SIM_SCORE: Final = 95
FINAL_SIM_MIN_BUDGET: Final = 160
CARRY_OVER_BONUS: Final = 5
TRACK_FLOOR_BONUS: Final = 10
TRACK_FLOOR_PCT: Final = 50
MAX_PLAN_ITEMS: Final = 5
FOCUS_LIMIT_SKILLS: Final = 2
MAX_LEARN_ITEMS: Final = 1
MAX_DIAGNOSTIC_ITEMS: Final = 1
FOCUS_FOLLOW_UP_MIN_MINUTES: Final = 30
OVER_TARGET_SHARE_PCT: Final = 20
OVER_TARGET_WINDOW_DAYS: Final = 14
TOO_HARD_WINDOW_DAYS: Final = 7
GUIDED_SEEN_MIN_DAYS: Final = 30
REINFORCE_CANONICAL_MIN_DAYS: Final = 7
SUBSTEP_DRILL: Final = MappingProxyType(
    {"below_points": 50, "min_low_rows": 2, "window_rows": 3, "min_delta": 5, "lookback_days": 28}
)
STAGE_LADDER: Final = ("LEARN", "RECALL", "GUIDED", "INDEPENDENT", "TIMED", "EXPLAIN", "TRANSFER", "SIMULATE")
SPECIAL_STAGE_STEP_DOWN: Final = MappingProxyType(
    {"PATTERN_DRILL": "GUIDED", "THINK_ALOUD": "INDEPENDENT", "REINFORCE": "GUIDED"}
)
MESSAGE_RULE_ORDER: Final = (
    "CALIBRATION",
    "DEADLINE_INFEASIBLE",
    "READINESS_LAPSED",
    "BACKLOG_OVER_BUDGET",
    "LEECH_RELEARN",
    "PREREQUISITE_UNLOCK",
    "NEW_TOPIC_HOLD",
    "SWITCH_TO_TIMED",
    "PATTERN_DRILL",
    "COMMUNICATION_GAP",
    "SUBSTEP_DRILL",
    "OVERCONFIDENT",
    "UNDERCONFIDENT",
    "MOCK_GAP",
    "STOP_STUDYING",
    "STUDIED_NOT_TESTED",
    "SHARPEN_FOCUS",
    "MOCK_DUE",
    "READINESS_BLOCKER",
    "READY_MAINTAIN",
    "DEFAULT",
)

# ---------------------------------------------------------------------------------------------------
# READINESS_MODEL.md (logic constants only; thresholds are role-profile gate_parameters)
# ---------------------------------------------------------------------------------------------------

READINESS_STATES: Final = ("NOT_MEASURED", "FOUNDATION", "DEVELOPING", "INTERVIEW_READY", "STRONG")
LAPSED_LOOKBACK_DAYS: Final = 30
