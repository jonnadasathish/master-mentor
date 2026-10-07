"""Cross-track communication (D-087): an optional "explain it aloud" step after technical practice.

The step is a communication prompt (an ``interview_question`` whose body lists what it ``explains``). It adds
communication evidence on the communication skill only; the technical observation is untouched, and the step
never blocks the technical task (see ``is_optional_step``). Pure and deterministic.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

COMMUNICATION_PREFIXES: Final = ("comm.", "communication.")
# Earlier stages (LEARN, RECALL, DIAGNOSE) have nothing to explain yet; revision and pattern drills are short.
EXPLAIN_STAGES: Final = ("GUIDED", "INDEPENDENT", "TIMED", "EXPLAIN", "TRANSFER")
RECENT_DAYS: Final = 3


def is_communication_skill(skill: str) -> bool:
    return skill.startswith(COMMUNICATION_PREFIXES)


@dataclass(frozen=True)
class ExplainCandidate:
    key: str
    title: str
    minutes: int
    skill: str  # the communication skill the step records on
    explains: tuple[str, ...]  # technical skill keys and/or component names it can follow
    position: int  # seed order


def pick_explain_item(
    *,
    skill: str,
    component: str,
    stage: str,
    candidates: Sequence[ExplainCandidate],
    done: Collection[str],
    recent_skills: Collection[str],
    room_minutes: int | None,
) -> ExplainCandidate | None:
    """The prompt that follows a session on ``skill``. ``room_minutes``: None = no budget."""
    if is_communication_skill(skill) or stage not in EXPLAIN_STAGES:
        return None
    best: tuple[tuple[int, int, int, str], ExplainCandidate] | None = None
    for c in candidates:
        if c.skill in recent_skills or (room_minutes is not None and c.minutes > room_minutes):
            continue
        if skill in c.explains:
            match = 0
        elif component in c.explains:
            match = 1
        else:
            continue
        rank = (match, int(c.key in done), c.position, c.key)
        if best is None or rank < best[0]:
            best = (rank, c)
    return best[1] if best else None


def is_optional_step(session_skill: str, content_has_explains: bool) -> bool:
    """A step is optional when it is a pairing prompt in a session about a non-communication skill."""
    return content_has_explains and not is_communication_skill(session_skill)


def recent_communication_skills(
    last_done_by_skill: Mapping[str, int | None], today_ordinal: int
) -> frozenset[str]:
    """Skills with an observation in the last ``RECENT_DAYS`` days (``last_done_by_skill``: date ordinal)."""
    return frozenset(
        s for s, last in last_done_by_skill.items() if last is not None and today_ordinal - last < RECENT_DAYS
    )
