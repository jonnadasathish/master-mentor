"""Starting profile, onboarding, personal roadmap and current-state read models (D-080)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.schemas.profile import GoalInput

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Technology = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
GroupKey = Annotated[str, StringConstraints(min_length=1, max_length=64)]

CLAIMS = ("strengths", "weaknesses", "never_studied", "recently_studied")
MAX_TECHNOLOGIES = 30
MAX_GROUPS_PER_CLAIM = 40


class ExperienceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    years: int | None = Field(default=None, ge=0, le=60)
    current_role: Short | None = None
    previous_role: Short | None = None


class SelfReportIn(BaseModel):
    """Skill-group keys the user believes fit each claim. Context only: never evidence."""

    model_config = ConfigDict(extra="forbid")

    strengths: list[GroupKey] = Field(default_factory=list, max_length=MAX_GROUPS_PER_CLAIM)
    weaknesses: list[GroupKey] = Field(default_factory=list, max_length=MAX_GROUPS_PER_CLAIM)
    never_studied: list[GroupKey] = Field(default_factory=list, max_length=MAX_GROUPS_PER_CLAIM)
    recently_studied: list[GroupKey] = Field(default_factory=list, max_length=MAX_GROUPS_PER_CLAIM)

    @field_validator("strengths", "weaknesses", "never_studied", "recently_studied")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _consistent(self) -> SelfReportIn:
        for a, b in (
            ("strengths", "weaknesses"),
            ("strengths", "never_studied"),
            ("never_studied", "recently_studied"),
        ):
            both = set(getattr(self, a)) & set(getattr(self, b))
            if both:
                raise ValueError(
                    f"{sorted(both)[0]} cannot be both {a.replace('_', ' ')} and {b.replace('_', ' ')}"
                )
        return self


class StartingProfileIn(BaseModel):
    """PUT /profile: fields not given keep their value."""

    model_config = ConfigDict(extra="forbid")

    display_name: Short | None = None
    experience: ExperienceIn | None = None
    technologies: list[Technology] | None = Field(default=None, max_length=MAX_TECHNOLOGIES)
    company_profile: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    self_report: SelfReportIn | None = None

    @field_validator("technologies")
    @classmethod
    def _dedupe(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: dict[str, str] = {}
        for item in value:
            seen.setdefault(item.casefold(), item)
        return list(seen.values())


class OnboardingIn(StartingProfileIn):
    """POST /onboarding/complete: the profile plus the goal (target date, weekday budgets, role profile)."""

    goal: GoalInput


class ExperienceOut(BaseModel):
    years: int | None
    current_role: str | None
    previous_role: str | None


class RoleOut(BaseModel):
    profile_key: str
    name: str
    seniority: str


class TargetOut(BaseModel):
    role: RoleOut
    target_date: date | None
    weekday_budgets: list[int]
    weekly_minutes: int
    phase: str
    weeks_left: str | None


class OnboardingOut(BaseModel):
    completed: bool
    completed_at: datetime | None


class StartingProfileOut(BaseModel):
    display_name: str
    timezone: str
    onboarding: OnboardingOut
    experience: ExperienceOut
    technologies: list[str]
    company_profile: str | None
    self_report: dict[str, list[str]]
    target: TargetOut | None
    available_roles: list[RoleOut]


# ------------------------------------------------------------------------------------------------ roadmap


class PrerequisiteOut(BaseModel):
    skill: str
    name: str
    score: int | None
    min_score: int


class RoadmapItemOut(BaseModel):
    skill_key: str
    name: str
    component: str
    bucket: str
    health: str
    score: int | None
    target: int
    status: str
    priority: int
    confidence: str
    declared_unknown: bool
    primary_gap_type: str | None
    focus_stage: str | None
    focus_skill: str | None
    focus_skill_name: str | None
    reason_codes: list[str]
    importance: int
    prerequisites: list[PrerequisiteOut]
    next_step_minutes: int | None


class WhyOut(BaseModel):
    skill_key: str
    name: str
    component: str
    score: int | None
    target: int
    importance: int
    priority: int
    reason_codes: list[str]
    metrics: dict[str, Any]
    prerequisites: list[PrerequisiteOut]


class FocusChangeOut(BaseModel):
    skill_key: str
    name: str
    priority_before: int | None
    priority_after: int | None
    reason_codes: list[str]


class ChangesOut(BaseModel):
    since: date
    changed: bool
    entered: list[FocusChangeOut]
    left: list[FocusChangeOut]


class BasedOnOut(BaseModel):
    role: RoleOut | None
    target_date: date | None
    weeks_left: str | None
    phase: str
    measured_skills: int
    required_skills: int
    blocked_skills: int
    overdue_reviews: int


class RoadmapSectionOut(BaseModel):
    count: int
    items: list[RoadmapItemOut]


class PersonalRoadmapOut(BaseModel):
    as_of_date: date
    calibration_phase: str
    available: bool  # false until at least one skill has evidence
    based_on: BasedOnOut
    focus_now: list[RoadmapItemOut]
    sections: dict[str, RoadmapSectionOut]  # build, consolidate, sharpen, maintain, parked, unmeasured, later
    why: list[WhyOut]
    changes: ChangesOut


class SelfReportedSkillOut(BaseModel):
    skill_key: str
    name: str
    score: int | None
    target: int | None
    confidence: str
    status: str
    declared_unknown: bool  # "new to me" from the familiarity sweep: itself a self-report, not a task result


class SelfReportedGroupOut(BaseModel):
    group_key: str
    name: str
    component: str
    claims: list[str]
    measured: int  # skills with task evidence (declared unknowns are not counted)
    total: int
    skills: list[SelfReportedSkillOut]


class StateSectionOut(BaseModel):
    count: int
    items: list[RoadmapItemOut]


class CurrentStateOut(BaseModel):
    as_of_date: date
    calibration_phase: str
    counts: dict[str, int]
    strong: StateSectionOut
    developing: StateSectionOut
    critical: StateSectionOut
    unknown: StateSectionOut
    self_reported: list[SelfReportedGroupOut]
