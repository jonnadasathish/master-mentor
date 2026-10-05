"""Cross-field rules for a raw problem attempt. Pure: returns field errors, never transforms values.

Single-field ranges (enums, 0-10, 1-5, non-negative) are enforced by the request schema; this module holds
the rules that relate several fields or need the current instant (passed in, never read).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.activity.vocabulary import ASSESSMENT_COMPONENTS, FUTURE_TOLERANCE_SECONDS, UNSCORED_KINDS


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


def attempt_errors(
    *,
    attempted_at: datetime,
    now_utc: datetime,
    timed: bool,
    time_seconds: int | None,
    time_limit_seconds: int | None,
    mistakes: tuple[str, ...],
) -> list[FieldError]:
    errors: list[FieldError] = []
    if attempted_at.tzinfo is None:
        errors.append(FieldError("attempted_at", "must include a timezone offset"))
    elif attempted_at > now_utc + timedelta(seconds=FUTURE_TOLERANCE_SECONDS):
        errors.append(FieldError("attempted_at", "cannot be in the future"))
    if timed and time_limit_seconds is None:
        errors.append(FieldError("time_limit_seconds", "required when timed is true"))
    if timed and time_seconds is None:
        errors.append(FieldError("time_seconds", "required when timed is true"))
    if not timed and time_limit_seconds is not None:
        errors.append(FieldError("time_limit_seconds", "only allowed when timed is true"))
    if len(set(mistakes)) != len(mistakes):
        errors.append(FieldError("mistakes", "each mistake code may appear only once"))
    return errors


def _timing_errors(
    *, timed: bool, time_seconds: int | None, time_limit_seconds: int | None
) -> list[FieldError]:
    errors: list[FieldError] = []
    if timed and time_limit_seconds is None:
        errors.append(FieldError("time_limit_seconds", "required when timed is true"))
    if timed and time_seconds is None:
        errors.append(FieldError("time_seconds", "required when timed is true"))
    if not timed and time_limit_seconds is not None:
        errors.append(FieldError("time_limit_seconds", "only allowed when timed is true"))
    return errors


@dataclass(frozen=True)
class AssessmentSkillFact:
    skill: str
    component: str | None  # None = unknown or inactive skill
    outcome_points: int | None


def assessment_errors(
    *,
    kind: str,
    observed_at: datetime,
    now_utc: datetime,
    timed: bool,
    time_seconds: int | None,
    time_limit_seconds: int | None,
    familiarity: str | None,
    study_minutes: int | None,
    skills: tuple[AssessmentSkillFact, ...],
) -> list[FieldError]:
    """Cross-field rules for an assessment (API_SPEC "Validation highlights")."""
    errors: list[FieldError] = []
    if observed_at.tzinfo is None:
        errors.append(FieldError("observed_at", "must include a timezone offset"))
    elif observed_at > now_utc + timedelta(seconds=FUTURE_TOLERANCE_SECONDS):
        errors.append(FieldError("observed_at", "cannot be in the future"))
    errors.extend(
        _timing_errors(timed=timed, time_seconds=time_seconds, time_limit_seconds=time_limit_seconds)
    )
    if kind == "SELF_ASSESSMENT" and familiarity is None:
        errors.append(FieldError("familiarity", "required for SELF_ASSESSMENT"))
    if kind != "SELF_ASSESSMENT" and familiarity is not None:
        errors.append(FieldError("familiarity", "only allowed on SELF_ASSESSMENT"))
    if kind == "STUDY_SESSION" and study_minutes is None:
        errors.append(FieldError("study_minutes", "required for STUDY_SESSION"))
    if kind != "STUDY_SESSION" and study_minutes is not None:
        errors.append(FieldError("study_minutes", "only allowed on STUDY_SESSION"))
    if not skills:
        errors.append(FieldError("skills", "at least one skill is required"))
    if len({s.skill for s in skills}) != len(skills):
        errors.append(FieldError("skills", "each skill may appear only once"))
    allowed = ASSESSMENT_COMPONENTS[kind]
    for s in skills:
        if s.component is None:
            errors.append(FieldError("skills", f"unknown or inactive skill {s.skill!r}"))
        elif s.component not in allowed:
            errors.append(FieldError("skills", f"{kind} cannot observe {s.component} skill {s.skill!r}"))
        if kind in UNSCORED_KINDS and s.outcome_points is not None:
            errors.append(FieldError("skills", f"{kind} has no outcome points ({s.skill!r})"))
        if kind not in UNSCORED_KINDS and s.outcome_points is None:
            errors.append(FieldError("skills", f"outcome_points required for {s.skill!r}"))
    return errors
