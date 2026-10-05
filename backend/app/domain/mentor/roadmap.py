"""Roadmap order for LEARN (MENTOR_ENGINE §4): current milestone per track and milestone completion. Pure."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from app.domain.catalog.model import Milestone
from app.domain.mentor.model import ExitFacts
from app.domain.profile.model import SkillGraph
from app.domain.skills.state import SkillState

MILESTONE_EXIT_LEVEL = 3

ExitCheck = Callable[[Milestone, Mapping[str, SkillState], SkillGraph, ExitFacts], bool]


def _t1_dsa_coding_l4(
    m: Milestone, states: Mapping[str, SkillState], graph: SkillGraph, f: ExitFacts
) -> bool:
    keys = [k for k, s in graph.skills.items() if s.tier == "T1" and s.component in ("dsa", "coding")]
    return all((states[k].level or 0) >= 4 for k in keys if k in states)


def _stories(m: Milestone, states: Mapping[str, SkillState], graph: SkillGraph, f: ExitFacts) -> bool:
    keys = [k for k in m.skills if k.startswith(("behavioral.", "communication."))]
    return all(f.stories_per_skill.get(k, 0) >= 2 for k in keys)


# Exact seed texts (seed/roadmap.yaml extra_exit). Unknown text never completes a milestone (conservative).
EXTRA_EXIT: dict[str, ExitCheck] = {
    "every T1 skill of components dsa and coding has level >= L4": _t1_dsa_coding_l4,
    "3 MACHINE_CODING assessments >= 70 on distinct exercises": lambda m, s, g, f: (
        f.machine_coding_passes >= 3
    ),
    "6 timed SD_DESIGN assessments >= 70 on distinct exercises": lambda m, s, g, f: f.timed_sd_passes >= 6,
    "2 stories exist for each behavioral/communication skill listed in BP-1": _stories,
    "gate G6 passes": lambda m, s, g, f: f.g6_passes,
}


def milestone_complete(
    m: Milestone, states: Mapping[str, SkillState], graph: SkillGraph, facts: ExitFacts
) -> bool:
    for key in m.skills:
        spec = graph.skills.get(key)
        if spec is None or not spec.required:
            continue
        state = states.get(key)
        if state is None or (state.level or 0) < MILESTONE_EXIT_LEVEL or not state.assessed:
            return False
    return all(text in EXTRA_EXIT and EXTRA_EXIT[text](m, states, graph, facts) for text in m.extra_exit)


def current_milestones(
    milestones: Sequence[Milestone], states: Mapping[str, SkillState], graph: SkillGraph, facts: ExitFacts
) -> dict[str, Milestone | None]:
    """Track -> first incomplete milestone in order (None = all complete)."""
    out: dict[str, Milestone | None] = {}
    for m in sorted(milestones, key=lambda x: (x.track_position, x.position)):
        if m.track in out:
            continue
        if not milestone_complete(m, states, graph, facts):
            out[m.track] = m
    for m in milestones:
        out.setdefault(m.track, None)
    return out


def milestone_of(milestones: Sequence[Milestone]) -> dict[str, Milestone]:
    return {skill: m for m in milestones for skill in m.skills}


def learn_allowed_by_roadmap(
    skill: str, milestones: Sequence[Milestone], current: Mapping[str, Milestone | None]
) -> bool:
    m = milestone_of(milestones).get(skill)
    if m is None:
        return True
    cur = current.get(m.track)
    return cur is None or m.position <= cur.position
