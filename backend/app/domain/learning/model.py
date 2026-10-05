"""Validated learning catalog (tracks → topics → skills, and content items). Immutable; seed-file order."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Topic:
    key: str
    track: str
    position: int  # 1-based within the track
    title: str
    summary: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class Track:
    key: str
    position: int
    title: str
    summary: str
    components: tuple[str, ...]
    topics: tuple[Topic, ...]


@dataclass(frozen=True)
class ContentItem:
    key: str
    type: str
    title: str
    skills: tuple[str, ...]  # first = primary skill
    minutes: int
    difficulty: str | None
    stages: tuple[str, ...]  # mentor stages this item serves (MENTOR_ENGINE stages)
    observation_kind: str
    time_limit_seconds: int | None
    problem_ids: tuple[int, ...]  # guided/timed problems
    body: Mapping[str, Any]
    position: int  # 1-based order across all content files (files sorted by name)
    source_file: str = ""

    @property
    def primary_skill(self) -> str:
        return self.skills[0]


@dataclass(frozen=True)
class LearningCatalog:
    tracks: tuple[Track, ...] = ()
    content: tuple[ContentItem, ...] = ()
    by_key: Mapping[str, ContentItem] = field(default_factory=dict)

    def for_skill(self, skill: str) -> tuple[ContentItem, ...]:
        """Content mapped to ``skill`` (primary or supporting), primary mappings first, then seed order."""
        primary = [c for c in self.content if c.skills[0] == skill]
        supporting = [c for c in self.content if skill in c.skills[1:]]
        return tuple(primary + supporting)

    def topic_of(self, skill: str) -> Topic | None:
        for track in self.tracks:
            for topic in track.topics:
                if skill in topic.skills:
                    return topic
        return None
