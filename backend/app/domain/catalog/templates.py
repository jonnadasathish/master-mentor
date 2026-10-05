"""Mission-template resolution (MISSION_LIBRARY.md §1): most specific match first, ties by lowest key.

1 component+stage+gap_type+applies_to  2 component+stage+applies_to  3 component+stage+gap_type
4 component+stage  5 generic+stage
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.domain.catalog.model import MissionTemplate


@dataclass(frozen=True)
class Resolution:
    template: MissionTemplate
    level: int  # 1 (most specific) .. 5 (generic fallback)


def applies_to_skill(template: MissionTemplate, skill_key: str) -> bool:
    if template.applies_to is None:
        return False
    return any(skill_key.startswith(p) if p.endswith(".") else skill_key == p for p in template.applies_to)


def resolve_template(
    templates: Iterable[MissionTemplate],
    *,
    component: str,
    stage: str,
    skill_key: str,
    gap_type: str | None = None,
) -> Resolution | None:
    candidates = [t for t in templates if stage in t.stages]

    def pick(level: int, matches: Sequence[MissionTemplate]) -> Resolution | None:
        return Resolution(min(matches, key=lambda t: t.key), level) if matches else None

    own = [t for t in candidates if t.component == component]
    with_gap = [t for t in own if gap_type is not None and t.gap_types and gap_type in t.gap_types]
    for level, matches in (
        (1, [t for t in with_gap if applies_to_skill(t, skill_key)]),
        (2, [t for t in own if t.applies_to and applies_to_skill(t, skill_key) and not t.gap_types]),
        (3, [t for t in with_gap if t.applies_to is None]),
        (4, [t for t in own if t.applies_to is None and not t.gap_types]),
        (5, [t for t in candidates if t.component == "generic"]),
    ):
        if (resolution := pick(level, matches)) is not None:
            return resolution
    return None
