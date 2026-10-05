"""Starting profile: self-reported context and the first-run flow (D-080).

The profile is configuration (like app_settings). It never feeds an engine: skill state comes only from
observations (CLAUDE.md rule 9; EVIDENCE_MODEL: self-report never raises a state). The goal (target role,
date, weekday budgets) stays in the versioned ``goals`` table and is changed through ``ProfileService``.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.errors import AppError
from app.models import AuditLog, RoleProfile, SkillGroup, StartingProfile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.envelope import ErrorCode
from app.schemas.profile import GoalPatch
from app.schemas.starting import (
    CLAIMS,
    ExperienceOut,
    OnboardingIn,
    OnboardingOut,
    RoleOut,
    StartingProfileIn,
    StartingProfileOut,
    TargetOut,
)
from app.services.activity_service import _validation
from app.services.profile_service import ProfileService

EMPTY_SELF_REPORT: dict[str, list[str]] = {c: [] for c in CLAIMS}


class StartingProfileService:
    def __init__(self, session: Session, clock: Clock, ruleset_version: str) -> None:
        self._s = session
        self._clock = clock
        self._ruleset_version = ruleset_version
        self._profiles = ProfileService(session, clock, ruleset_version)
        self._repo = ProfileRepository(session)

    def _now(self) -> Any:
        return self._clock.now_utc().astimezone(UTC).replace(tzinfo=None)

    def _row(self) -> StartingProfile:
        row = self._s.get(StartingProfile, 1)
        if row is None:  # a database restored without the bootstrap row: create it on first use
            row = StartingProfile(
                id=1,
                technologies_json=[],
                self_report_json={c: [] for c in CLAIMS},
                updated_at=self._now(),
            )
            self._s.add(row)
            self._s.flush()
        return row

    def _audit(self, action: str, payload: dict[str, object]) -> None:
        self._s.add(
            AuditLog(
                at=self._now(),
                entity_type="starting_profile",
                entity_id="1",
                action=action,
                payload_json=payload,
            )
        )

    # ------------------------------------------------------------------ read
    def _roles(self) -> list[RoleOut]:
        rows = self._s.scalars(select(RoleProfile).order_by(RoleProfile.profile_key))
        return [RoleOut(profile_key=r.profile_key, name=r.name, seniority=r.seniority) for r in rows]

    def _target(self) -> TargetOut | None:
        goal = self._repo.goal_on(self._profiles.today())
        if goal is None:
            return None
        active = self._profiles.active_goal()
        role = next((r for r in self._roles() if r.profile_key == active.profile_key), None)
        if role is None:
            return None
        return TargetOut(
            role=role,
            target_date=active.target_date,
            weekday_budgets=active.weekday_budgets,
            weekly_minutes=active.weekly_minutes,
            phase=active.phase,
            weeks_left=active.weeks_left,
        )

    def get(self) -> StartingProfileOut:
        row = self._row()
        settings = self._profiles.settings()
        report = {c: list(row.self_report_json.get(c, [])) for c in CLAIMS}
        return StartingProfileOut(
            display_name=settings.display_name,
            timezone=settings.timezone,
            onboarding=OnboardingOut(
                completed=row.onboarding_completed_at is not None,
                completed_at=None
                if row.onboarding_completed_at is None
                else row.onboarding_completed_at.replace(tzinfo=UTC),
            ),
            experience=ExperienceOut(
                years=row.experience_years, current_role=row.current_role, previous_role=row.previous_role
            ),
            technologies=list(row.technologies_json),
            company_profile=row.company_profile,
            self_report=report,
            target=self._target(),
            available_roles=self._roles(),
        )

    # ------------------------------------------------------------------ write
    def _validate_groups(self, report: dict[str, list[str]]) -> None:
        known = set(self._s.scalars(select(SkillGroup.group_key)))
        errors = [
            (f"self_report.{claim}", f"unknown skill group {key!r}")
            for claim, keys in report.items()
            for key in keys
            if key not in known
        ]
        if errors:
            raise _validation(errors)

    def _apply(self, row: StartingProfile, payload: StartingProfileIn) -> dict[str, object]:
        before: dict[str, object] = {
            "experience_years": row.experience_years,
            "current_role": row.current_role,
            "previous_role": row.previous_role,
            "technologies": list(row.technologies_json),
            "company_profile": row.company_profile,
            "self_report": dict(row.self_report_json),
        }
        if payload.experience is not None:
            e = payload.experience.model_fields_set
            if "years" in e:
                row.experience_years = payload.experience.years
            if "current_role" in e:
                row.current_role = payload.experience.current_role
            if "previous_role" in e:
                row.previous_role = payload.experience.previous_role
        if payload.technologies is not None:
            row.technologies_json = list(payload.technologies)
        if payload.company_profile is not None:
            row.company_profile = payload.company_profile or None
        if payload.self_report is not None:
            report = {c: list(getattr(payload.self_report, c)) for c in CLAIMS}
            self._validate_groups(report)
            row.self_report_json = report
        if payload.display_name is not None:
            settings = self._repo.settings()
            if settings is None:
                raise AppError(ErrorCode.INVALID_STATE, "Settings are not initialized; run migrations.", 409)
            before["display_name"] = settings.display_name
            settings.display_name = payload.display_name
        row.updated_at = self._now()
        return before

    def update(self, payload: StartingProfileIn) -> StartingProfileOut:
        row = self._row()
        before = self._apply(row, payload)
        self._audit(
            "UPDATE_STARTING_PROFILE",
            {"before": before, "after": payload.model_dump(exclude_unset=True, mode="json")},
        )
        self._s.commit()
        return self.get()

    def complete(self, payload: OnboardingIn) -> StartingProfileOut:
        """The wizard's last step: profile, goal (new version when changed) and the first-run flag."""
        # Goal first: it validates the dates/budgets and raises before anything is half-written.
        has_goal = self._repo.goal_on(self._profiles.today()) is not None
        goal_body = payload.goal
        if has_goal:
            self._profiles.patch_goal(GoalPatch(**goal_body.model_dump(exclude_unset=True)))
        else:
            self._profiles.create_goal(goal_body)
        row = self._row()
        profile_part = StartingProfileIn(**payload.model_dump(exclude={"goal"}, exclude_unset=True))
        before = self._apply(row, profile_part)
        first_time = row.onboarding_completed_at is None
        if first_time:
            row.onboarding_completed_at = self._now()
        self._audit(
            "COMPLETE_ONBOARDING" if first_time else "REDO_ONBOARDING",
            {"before": before, "after": payload.model_dump(exclude_unset=True, mode="json")},
        )
        self._s.commit()
        return self.get()
