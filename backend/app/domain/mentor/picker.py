"""Problem picker (MENTOR_ENGINE §7). Pure; deterministic ordering: fewest attempts, then platform_key."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import date

from app.domain.mentor.model import ProblemInfo
from app.domain.profile.model import SkillGraph
from app.domain.skills.state import SkillState

STAGE_DIFFICULTY = {
    "DIAGNOSE": "MEDIUM",
    "LEARN": "EASY",
    "GUIDED": "EASY",
    "THINK_ALOUD": "MEDIUM",
    "INDEPENDENT": "MEDIUM",
    "TIMED": "MEDIUM",
    "EXPLAIN": "MEDIUM",
    "SIMULATE": "MEDIUM",
    "TRANSFER": "HARD",
}
SEEN_OK_DAYS = {"LEARN": 30, "GUIDED": 30}
REINFORCE_MIN_DAYS = 7
PATTERN_DRILL_TARGET = 2
PATTERN_DRILL_TOTAL = 5
PATTERN_RECOGNITION = "dsa.pattern_recognition"


def _order(p: ProblemInfo) -> tuple[int, str]:
    return (p.attempt_count, p.platform_key)


def _seen_ok(p: ProblemInfo, stage: str, as_of: date) -> bool:
    if p.attempt_count == 0:
        return True
    days = SEEN_OK_DAYS.get(stage)
    return days is not None and p.last_attempt_on is not None and (as_of - p.last_attempt_on).days >= days


def _mapped(problems: Sequence[ProblemInfo], skill: str) -> list[ProblemInfo]:
    primary = [p for p in problems if p.primary() == skill]
    return primary or [p for p in problems if any(s == skill for s, _ in p.skills)]


def _pools(problems: Sequence[ProblemInfo], skill: str) -> list[list[ProblemInfo]]:
    """Primary mappings, then secondary; a skill no problem maps (execution.*) may use any problem (D-069)."""
    primary = [p for p in problems if p.primary() == skill]
    secondary = [p for p in problems if p.primary() != skill and any(s == skill for s, _ in p.skills)]
    if not primary and not secondary:
        return [list(problems)]
    return [primary, secondary]


def pick_problem(
    *,
    stage: str,
    skill: str,
    tier: str,
    problems: Sequence[ProblemInfo],
    as_of: date,
    exclude: Collection[int] = (),
) -> int | None:
    pool = [p for p in problems if p.id not in exclude]
    if stage == "REINFORCE":
        canonical = [
            p
            for p in _mapped(pool, skill)
            if p.is_canonical
            and (p.last_attempt_on is None or (as_of - p.last_attempt_on).days >= REINFORCE_MIN_DAYS)
        ]
        return min(canonical, key=_order).id if canonical else None
    wanted = STAGE_DIFFICULTY.get(stage, "MEDIUM")
    if stage == "DIAGNOSE" and tier == "T3":
        wanted = "EASY"
    for mapped in _pools(pool, skill):
        candidates = [p for p in mapped if _seen_ok(p, stage, as_of)]
        for difficulty in (wanted, "MEDIUM"):  # relax one step toward MEDIUM
            found = sorted((p for p in candidates if p.difficulty == difficulty), key=_order)
            if found:
                return found[0].id
    return None


def pattern_drill_statements(
    *,
    skill: str,
    problems: Sequence[ProblemInfo],
    graph: SkillGraph,
    states: Mapping[str, SkillState],
    exclude: Collection[int] = (),
) -> tuple[int, ...] | None:
    """5 unseen statements: 2 primary to the target pattern + 3 from distinct other patterns at level >= L1
    (for dsa.pattern_recognition: 5 distinct patterns)."""
    unseen = sorted((p for p in problems if p.attempt_count == 0 and p.id not in exclude), key=_order)
    known = {
        k
        for k, s in graph.skills.items()
        if s.is_pattern and k in states and states[k].level is not None and (states[k].level or 0) >= 1
    }
    picked: list[int] = []
    patterns: set[str] = set()
    if skill != PATTERN_RECOGNITION:
        own = [p.id for p in unseen if p.primary() == skill][:PATTERN_DRILL_TARGET]
        if len(own) < PATTERN_DRILL_TARGET:
            return None
        picked.extend(own)
        patterns.add(skill)
    for p in unseen:
        if len(picked) >= PATTERN_DRILL_TOTAL:
            break
        primary = p.primary()
        if primary is None or primary in patterns or primary not in known or p.id in picked:
            continue
        picked.append(p.id)
        patterns.add(primary)
    return tuple(picked) if len(picked) == PATTERN_DRILL_TOTAL else None


def greedy_cover(
    *,
    target_skills: Collection[str],
    unassessed: Collection[str],
    problems: Sequence[ProblemInfo],
    difficulty: str,
    count: int,
    exclude: Collection[int] = (),
) -> tuple[int, ...]:
    """Pick unseen problems one at a time, each covering the most not-yet-covered unassessed target skills."""
    open_skills = {s for s in target_skills if s in unassessed}
    pool = [
        p
        for p in problems
        if p.attempt_count == 0
        and p.difficulty == difficulty
        and p.id not in exclude
        and any(s in target_skills for s, _ in p.skills)
    ]
    picked: list[int] = []
    for _ in range(count):
        best = sorted(
            (p for p in pool if p.id not in picked),
            key=lambda p: (-len({s for s, _ in p.skills} & open_skills), _order(p)),
        )
        if not best:
            break
        choice = best[0]
        picked.append(choice.id)
        open_skills -= {s for s, _ in choice.skills}
    return tuple(picked)
