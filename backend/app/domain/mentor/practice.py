"""Practice minutes (MENTOR_ENGINE §5): per skill per local day, aggregated for a plan date. Pure."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.mentor.model import PracticeSummary
from app.domain.profile.model import ProfileSpec, SkillGraph


@dataclass(frozen=True)
class PracticeObservation:
    observed_on: date
    skills: tuple[str, ...]  # attempts: (primary skill,); assessments: all skills
    time_seconds: int | None = None
    study_minutes: int | None = None
    plan_item_minutes: int | None = None
    is_study: bool = False


def observation_minutes(o: PracticeObservation) -> int:
    if o.time_seconds is not None:
        return o.time_seconds // 60
    if o.study_minutes is not None:
        return o.study_minutes
    return o.plan_item_minutes or 0


def split_minutes(o: PracticeObservation) -> dict[str, int]:
    """Equal split across skills; the remainder goes to the first skill by key."""
    if not o.skills:
        return {}
    minutes = observation_minutes(o)
    keys = sorted(o.skills)
    share, remainder = divmod(minutes, len(keys))
    out = dict.fromkeys(keys, share)
    out[keys[0]] += remainder
    return out


def summarize_practice(
    observations: Sequence[PracticeObservation], as_of: date, graph: SkillGraph, profile: ProfileSpec
) -> PracticeSummary:
    """Windows are [as_of - N, as_of - 1] (today's work is not history yet)."""
    track_of = {c.key: c.track for c in profile.components}
    tracks: dict[str, int] = dict.fromkeys(profile.track_minutes, 0)
    s7: dict[str, int] = {}
    s14: dict[str, int] = {}
    study7: dict[str, int] = {}
    total14 = 0
    for o in observations:
        age = (as_of - o.observed_on).days
        if age < 1 or age > 14:
            continue
        for skill, minutes in split_minutes(o).items():
            s14[skill] = s14.get(skill, 0) + minutes
            total14 += minutes
            if age <= 7:
                s7[skill] = s7.get(skill, 0) + minutes
                if o.is_study:
                    study7[skill] = study7.get(skill, 0) + minutes
                spec = graph.skills.get(skill)
                track = track_of.get(spec.component) if spec else None
                if track is not None:
                    tracks[track] = tracks.get(track, 0) + minutes
    return PracticeSummary(
        track_minutes_7d=tracks,
        skill_minutes_7d=s7,
        skill_minutes_14d=s14,
        study_minutes_7d=study7,
        total_minutes_14d=total14,
    )
