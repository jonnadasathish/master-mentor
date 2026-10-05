"""Closed vocabularies and structural rules of the catalog (GLOSSARY.md, SKILL_GRAPH.md, MISSION_LIBRARY.md).

These are catalog validation rules, versioned with the seed (``seed_version``). They are deliberately
NOT ruleset constants: mentor formulas (``app.domain.rulesets``) and catalog structure evolve independently.
"""

from __future__ import annotations

import re
from typing import Final

COMPONENTS: Final = ("dsa", "coding", "cs", "lld", "system_design", "behavioral", "project")
TEMPLATE_ONLY_COMPONENTS: Final = ("generic", "revision", "mock")
TEMPLATE_COMPONENTS: Final = COMPONENTS + TEMPLATE_ONLY_COMPONENTS

STAGES: Final = (
    "DIAGNOSE",
    "LEARN",
    "RECALL",
    "GUIDED",
    "INDEPENDENT",
    "TIMED",
    "EXPLAIN",
    "TRANSFER",
    "SIMULATE",
    "PATTERN_DRILL",
    "THINK_ALOUD",
    "REINFORCE",
    "REVISION",
)
# Stages the gap engine can recommend for a skill of any component (MISSION_LIBRARY.md §1 coverage rule).
GAP_STAGES: Final = tuple(stage for stage in STAGES if stage != "REVISION")
NEXT_STAGE_TOKENS: Final = STAGES + ("GAP_ENGINE", "MOCK")

GAP_TYPES: Final = (
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
# ITEM_DEFINED: the observation kind is decided by the revision item being reviewed.
OBSERVATION_KINDS: Final = ASSESSMENT_KINDS + ("ATTEMPT", "MOCK", "ITEM_DEFINED")

EVIDENCE_KINDS: Final = (
    "attempt",
    "recall",
    "pattern_drill",
    "practice",
    "timed",
    "followup",
    "applied",
    "mock_round",
)
DIFFICULTIES: Final = ("EASY", "MEDIUM", "HARD")
PLATFORMS: Final = ("LEETCODE", "OTHER")
ROUND_TYPES: Final = ("DSA", "CS", "LLD", "SYSTEM_DESIGN", "BEHAVIORAL", "PROJECT_DEEP_DIVE")
TIERS: Final = ("T1", "T2", "T3", "T4")
REVISION_ITEM_TYPES: Final = (
    "PROBLEM",
    "PATTERN",
    "CS",
    "CONCEPT",
    "SD",
    "BEHAVIORAL",
    "MOCK_WEAKNESS",
    "ANY",
)

ALLOWED_MIN_SCORES: Final = (30, 45, 60)
MAPPING_WEIGHTS_BP: Final = (5000, 10000)
PRIMARY_MAPPING_BP: Final = 10000
MAX_PREREQUISITE_DEPTH: Final = 6  # SKILL_GRAPH.md §2 (seed-v1 measured depth); deeper chains need a decision
WEEKLY_MINUTES: Final = 600  # 10 h/week (ROLE_PROFILE.md §1)

SKILL_KEY_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
SEED_VERSION_PATTERN: Final = re.compile(r"^seed-v[1-9][0-9]*$")

SEED_FILES: Final = {
    "skill_graph": "skills.yaml",
    "problem_catalog": "problems.yaml",
    "roadmap": "roadmap.yaml",
    "mission_templates": "mission_templates.yaml",
}
ROLE_PROFILE_DIR: Final = "role_profiles"
LOCK_FILE: Final = "seed.lock.yaml"
