"""Component scores and coverage (READINESS_MODEL.md §3). Pure.

Over the **required** skills of a component (T1–T3; parked skills included; unassessed count as 0).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.domain.profile.model import ProfileSpec, SkillGraph
from app.domain.skills.state import SkillState, round_half_up


@dataclass(frozen=True)
class ComponentScore:
    component: str
    score: int
    assessed_pct: int
    medium_conf_pct: int
    required_skills: int


@dataclass(frozen=True)
class ComponentScores:
    components: Mapping[str, ComponentScore]  # profile order
    weighted_score: int  # display only
    limiting_component: str | None

    def score(self, component: str) -> int:
        return self.components[component].score


def calculate_component_scores(
    states: Mapping[str, SkillState], graph: SkillGraph, profile: ProfileSpec
) -> ComponentScores:
    out: dict[str, ComponentScore] = {}
    for comp in profile.components:
        required = [s for s in graph.skills.values() if s.component == comp.key and s.required]
        weight_sum = sum(s.importance for s in required)
        numerator = sum(s.importance * (_effective(states.get(s.key))) for s in required)
        score = round_half_up(Decimal(numerator) / Decimal(weight_sum)) if weight_sum else 0
        n = len(required)
        assessed = sum(1 for s in required if _confidence(states.get(s.key)) != "NONE")
        medium = sum(1 for s in required if _confidence(states.get(s.key)) in ("MEDIUM", "HIGH"))
        out[comp.key] = ComponentScore(
            component=comp.key,
            score=score,
            assessed_pct=100 * assessed // n if n else 0,
            medium_conf_pct=100 * medium // n if n else 0,
            required_skills=n,
        )
    weighted = round_half_up(
        Decimal(sum(c.weight * out[c.key].score for c in profile.components)) / Decimal(100)
    )
    limiting = None
    if profile.components:
        limiting = sorted(profile.components, key=lambda c: (-(c.gate - out[c.key].score), -c.weight, c.key))[
            0
        ].key
    return ComponentScores(out, weighted, limiting)


def _effective(state: SkillState | None) -> int:
    return state.effective_score if state is not None and state.effective_score is not None else 0


def _confidence(state: SkillState | None) -> str:
    return state.confidence if state is not None else "NONE"
