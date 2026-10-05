"""Engine-facing view of the catalog + role profile: skills with their tier targets, prerequisites,
topological order, components, tracks. Built from a validated ``Catalog`` (tests, golden scenarios) or
from the loaded DB catalog (services) — both produce the same immutable values.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from app.domain.catalog.model import Catalog


@dataclass(frozen=True)
class SkillSpec:
    key: str
    component: str
    group: str
    is_pattern: bool
    tier: str
    importance: int
    target: int
    floor: int
    required: bool
    prerequisites: tuple[tuple[str, int], ...]  # (prerequisite key, min_score), seed order


@dataclass(frozen=True)
class ComponentSpec:
    key: str
    name: str
    weight: int
    gate: int
    stretch: int
    track: str


@dataclass(frozen=True)
class ProfileSpec:
    profile_key: str
    components: tuple[ComponentSpec, ...]
    track_minutes: Mapping[str, int]
    track_components: Mapping[str, tuple[str, ...]]
    gate_parameters: Mapping[str, object]
    final_simulation: Mapping[str, object]
    weekday_budgets_default: tuple[int, ...]
    round_types: tuple[str, ...] = ()  # interview loop order (mock round types)
    round_minutes: Mapping[str, int] = field(default_factory=dict)

    def component(self, key: str) -> ComponentSpec:
        return next(c for c in self.components if c.key == key)


@dataclass(frozen=True)
class SkillGraph:
    skills: Mapping[str, SkillSpec]  # seed order
    topological_order: tuple[str, ...]  # prerequisites before dependents
    dependents: Mapping[str, tuple[str, ...]] = field(default_factory=dict)  # direct dependents, seed order

    @staticmethod
    def build(skills: Sequence[SkillSpec], topological_order: Sequence[str]) -> SkillGraph:
        dependents: dict[str, list[str]] = {s.key: [] for s in skills}
        for s in skills:
            for prereq, _ in s.prerequisites:
                dependents[prereq].append(s.key)
        return SkillGraph(
            {s.key: s for s in skills}, tuple(topological_order), {k: tuple(v) for k, v in dependents.items()}
        )


@dataclass(frozen=True)
class Goal:
    """The goal version valid on ``as_of_date`` (DATA_MODEL §3)."""

    id: int | None
    target_date: date | None
    weekday_budgets: tuple[int, ...]  # Mon..Sun minutes


def profile_from_config(profile_key: str, config: Mapping[str, object]) -> ProfileSpec:
    components = tuple(
        ComponentSpec(
            key=str(c["key"]),
            name=str(c["name"]),
            weight=int(c["weight"]),
            gate=int(c["gate"]),
            stretch=int(c["stretch"]),
            track=str(c["track"]),
        )
        for c in config["components"]  # type: ignore[attr-defined]
    )
    tracks: Mapping[str, Mapping[str, object]] = config["tracks"]  # type: ignore[assignment]
    loop: list[Mapping[str, object]] = list(config.get("interview_loop", []))  # type: ignore[call-overload]
    round_minutes: dict[str, int] = {}
    for r in loop:
        rt = r.get("round_type")
        if rt is not None and str(rt) not in round_minutes:
            round_minutes[str(rt)] = int(str(r["minutes"]))
    return ProfileSpec(
        profile_key=profile_key,
        components=components,
        track_minutes={k: int(v["minutes"]) for k, v in tracks.items()},  # type: ignore[call-overload]
        track_components={k: tuple(v.get("components", ())) for k, v in tracks.items()},  # type: ignore[arg-type]
        gate_parameters=dict(config.get("gate_parameters", {})),  # type: ignore[call-overload]
        final_simulation=dict(config.get("final_simulation", {})),  # type: ignore[call-overload]
        weekday_budgets_default=tuple(int(x) for x in config.get("weekday_budgets_default", ())),  # type: ignore[attr-defined]
        round_types=tuple(round_minutes),
        round_minutes=round_minutes,
    )


def from_catalog(catalog: Catalog, profile_key: str | None = None) -> tuple[SkillGraph, ProfileSpec]:
    profile = next(p for p in catalog.profiles if profile_key is None or p.profile_key == profile_key)
    targets = {t.skill: t for t in profile.targets}
    specs = [
        SkillSpec(
            key=s.key,
            component=s.component,
            group=s.parent,
            is_pattern=s.is_pattern,
            tier=targets[s.key].tier,
            importance=targets[s.key].importance,
            target=targets[s.key].target_score,
            floor=targets[s.key].floor_score,
            required=targets[s.key].required,
            prerequisites=tuple((p.skill, p.min_score) for p in s.prerequisites),
        )
        for s in catalog.skills
    ]
    return SkillGraph.build(specs, catalog.topological_order), profile_from_config(
        profile.profile_key, profile.config
    )
