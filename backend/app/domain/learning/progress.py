"""Learning progress, derived from the learner's own observations (no progress table; rebuildable)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem


@dataclass(frozen=True)
class ContentObservation:
    source_key: str
    points: int | None  # None for STUDY_SESSION
    observed_on: date
    observation_id: int


@dataclass(frozen=True)
class ContentProgress:
    key: str
    completions: int
    last_points: int | None
    best_points: int | None
    last_on: date | None
    passed: bool | None  # None: nothing scored (reading) or not attempted
    milestones_done: tuple[str, ...] = ()
    defended: bool = False


def parse_source_key(source_key: str) -> tuple[str, str | None] | None:
    """``content:<key>`` or ``content:<key>#<part>`` -> (key, part); anything else -> None."""
    if not source_key.startswith(lv.SOURCE_KEY_PREFIX):
        return None
    rest = source_key[len(lv.SOURCE_KEY_PREFIX) :]
    key, _, part = rest.partition("#")
    return key, (part or None)


def pass_mark(item: ContentItem) -> int | None:
    if item.type in lv.CHECK_TYPES:
        return lv.CHECK_PASS_POINTS
    if item.type in lv.RUBRIC_TYPES or item.type in lv.PROJECT_TYPES:
        return lv.RUBRIC_PASS_POINTS
    return None


def content_progress(
    observations: Sequence[ContentObservation], catalog: Mapping[str, ContentItem]
) -> dict[str, ContentProgress]:
    grouped: dict[str, list[tuple[ContentObservation, str | None]]] = {}
    for o in observations:
        parsed = parse_source_key(o.source_key)
        if parsed is None or parsed[0] not in catalog:
            continue
        grouped.setdefault(parsed[0], []).append((o, parsed[1]))
    out: dict[str, ContentProgress] = {}
    for key, rows in grouped.items():
        item = catalog[key]
        rows.sort(key=lambda r: (r[0].observed_on, r[0].observation_id))
        mark = pass_mark(item)
        if item.type == "project":
            milestones = tuple(
                m["key"]
                for m in item.body["milestones"]
                if any(part == m["key"] and (o.points or 0) >= lv.RUBRIC_PASS_POINTS for o, part in rows)
            )
            defended = any(part == "defense" and (o.points or 0) >= lv.RUBRIC_PASS_POINTS for o, part in rows)
            total = len(item.body["milestones"])
            out[key] = ContentProgress(
                key,
                len(rows),
                rows[-1][0].points,
                _best(rows),
                rows[-1][0].observed_on,
                len(milestones) == total and defended,
                milestones,
                defended,
            )
            continue
        best = _best(rows)
        passed = None if mark is None or best is None else best >= mark
        out[key] = ContentProgress(key, len(rows), rows[-1][0].points, best, rows[-1][0].observed_on, passed)
    return out


def _best(rows: Sequence[tuple[ContentObservation, str | None]]) -> int | None:
    scored = [o.points for o, _ in rows if o.points is not None]
    return max(scored) if scored else None
