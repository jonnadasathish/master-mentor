"""Content coverage report (MASTER_SPEC_V3 §26). Pure: catalog facts in, one deterministic row per
skill out."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.communication.vocabulary import is_optional_communication_skill
from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem, LearningCatalog


@dataclass(frozen=True)
class SkillFacts:
    key: str
    name: str
    component: str
    tier: str | None
    importance: int
    required: bool


@dataclass(frozen=True)
class CoverageRow:
    skill_key: str
    skill_name: str
    component: str
    tracks: tuple[str, ...]
    tier: str | None
    importance: int
    required: bool
    direct_learning_content: int
    concept_checks: int
    practice_count: int
    timed_practice: int
    revision_content: int
    mock_coverage: tuple[str, ...]  # round types of the interview loop that test this skill's component
    coverage_state: str


def coverage_state(learning: int, checks: int, practice: int, timed: int, revision: int) -> str:
    if learning == 0 and checks == 0 and practice == 0:
        return "CONTENT_GAP"
    if checks == 0 and practice == 0:
        return "UNMEASURED"  # can be read about but nothing produces scoring evidence
    if learning and checks and practice and timed and revision:
        return "FULL"
    return "PARTIAL"


def _timed(c: ContentItem) -> bool:
    return c.type == "timed_problem" or c.time_limit_seconds is not None


def coverage_report(
    skills: Sequence[SkillFacts],
    learning: LearningCatalog,
    problems_by_skill: Mapping[str, Sequence[str]],  # skill -> difficulties of mapped problems
    rounds_by_component: Mapping[str, Sequence[str]],
) -> tuple[CoverageRow, ...]:
    tracks_of: dict[str, list[str]] = {}
    for track in learning.tracks:
        for topic in track.topics:
            for key in topic.skills:
                if track.key not in tracks_of.setdefault(key, []):
                    tracks_of[key].append(track.key)
    rows: list[CoverageRow] = []
    for s in skills:
        items = learning.for_skill(s.key)
        reading = sum(1 for c in items if c.type in lv.READING_TYPES)
        checks = sum(1 for c in items if c.type in ("concept_check", "quiz"))
        revision = sum(1 for c in items if c.type == "revision_card")
        practice_items = [c for c in items if c.type in lv.RUBRIC_TYPES + lv.PROBLEM_TYPES + lv.PROJECT_TYPES]
        mapped = list(problems_by_skill.get(s.key, ()))
        practice = len(practice_items) + len(mapped)
        timed = sum(1 for c in practice_items if _timed(c)) + sum(
            1 for d in mapped if d in ("MEDIUM", "HARD")
        )
        rows.append(
            CoverageRow(
                s.key,
                s.name,
                s.component,
                tuple(tracks_of.get(s.key, ())),
                s.tier,
                s.importance,
                s.required,
                reading,
                checks,
                practice,
                timed,
                revision,
                ()
                if is_optional_communication_skill(s.key)
                else tuple(rounds_by_component.get(s.component, ())),
                coverage_state(reading, checks, practice, timed, revision),
            )
        )
    return tuple(rows)


def summarize_coverage(rows: Sequence[CoverageRow]) -> dict[str, dict[str, int]]:
    """Counts per state, overall and for required skills only."""
    out: dict[str, dict[str, int]] = {"all": {}, "required": {}}
    for state in lv.COVERAGE_STATES:
        out["all"][state] = sum(1 for r in rows if r.coverage_state == state)
        out["required"][state] = sum(1 for r in rows if r.required and r.coverage_state == state)
    return out
