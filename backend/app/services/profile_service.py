"""Settings and versioned goals (API_SPEC "Settings and goal"). Every change is audited and triggers a run."""

from __future__ import annotations

from datetime import UTC, date
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.domain.clock import Clock, local_date
from app.domain.gaps.engine import prep_phase
from app.domain.profile.goals import goal_errors
from app.domain.rulesets import get_ruleset
from app.errors import AppError
from app.models import AuditLog, Goal, RoleProfile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.envelope import ErrorCode
from app.schemas.profile import ActiveGoalOut, GoalInput, GoalOut, GoalPatch, SettingsOut, SettingsPatch
from app.services.activity_service import FALLBACK_TIMEZONE, _validation

DEFAULT_WEEKDAY_BUDGETS = [90, 90, 90, 90, 90, 75, 75]  # ROLE_PROFILE default (D-034)


class ProfileService:
    def __init__(self, session: Session, clock: Clock, ruleset_version: str) -> None:
        self._s = session
        self._clock = clock
        self._repo = ProfileRepository(session)
        self._ruleset = get_ruleset(ruleset_version)

    def today(self) -> date:
        settings = self._repo.settings()
        return local_date(self._clock.now_utc(), settings.timezone if settings else FALLBACK_TIMEZONE)

    def _audit(self, entity_type: str, entity_id: str, action: str, payload: dict[str, object]) -> None:
        self._s.add(
            AuditLog(
                at=self._clock.now_utc().astimezone(UTC).replace(tzinfo=None),
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload_json=payload,
            )
        )

    # ------------------------------------------------------------------ settings
    def settings(self) -> SettingsOut:
        row = self._repo.settings()
        if row is None:
            raise AppError(ErrorCode.INVALID_STATE, "Settings are not initialized; run migrations.", 409)
        return SettingsOut(timezone=row.timezone, display_name=row.display_name)

    def update_settings(self, patch: SettingsPatch) -> SettingsOut:
        row = self._repo.settings()
        if row is None:
            raise AppError(ErrorCode.INVALID_STATE, "Settings are not initialized; run migrations.", 409)
        if patch.timezone is not None:
            try:
                ZoneInfo(patch.timezone)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise _validation([("timezone", "unknown IANA timezone")]) from exc
        before = {"timezone": row.timezone, "display_name": row.display_name}
        if patch.timezone is not None:
            row.timezone = patch.timezone
        if patch.display_name is not None:
            row.display_name = patch.display_name
        self._audit("app_settings", "1", "UPDATE_SETTINGS", {"before": before, "after": patch.model_dump()})
        self._s.commit()
        return self.settings()

    # ------------------------------------------------------------------ goals
    def _profile(self, profile_key: str | None, fallback_id: int | None) -> RoleProfile:
        profile = (
            self._repo.profile_by_key(profile_key)
            if profile_key is not None
            else self._repo.profile_row(fallback_id)
        )
        if profile is None:
            raise AppError(
                ErrorCode.NOT_FOUND if profile_key else ErrorCode.INVALID_STATE,
                f"Role profile {profile_key!r} not found."
                if profile_key
                else "No role profile loaded; run make seed.",
                404 if profile_key else 409,
            )
        return profile

    def _out(self, goal: Goal) -> GoalOut:
        profile = self._repo.profile_row(goal.role_profile_id)
        return GoalOut(
            id=goal.id,
            profile_key=profile.profile_key if profile else "?",
            target_date=goal.target_date,
            weekday_budgets=list(goal.weekday_budgets_json),
            weekly_minutes=sum(goal.weekday_budgets_json),
            valid_from=goal.valid_from,
            valid_to=goal.valid_to,
            is_active=goal.valid_to is None,
            created_at=goal.created_at.replace(tzinfo=UTC),
        )

    def active_goal(self) -> ActiveGoalOut:
        today = self.today()
        goal = self._repo.goal_on(today)
        if goal is None:
            raise AppError(ErrorCode.NOT_FOUND, "No active goal; create one with POST /goals.", 404)
        phase, weeks = prep_phase(goal.target_date, today, self._ruleset)
        return ActiveGoalOut(
            **self._out(goal).model_dump(),
            phase=phase,
            weeks_left=None if weeks is None else str(weeks.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
        )

    def history(self) -> list[GoalOut]:
        return [self._out(g) for g in self._repo.goals()]

    def _new_version(
        self,
        *,
        profile: RoleProfile,
        target_date: date | None,
        budgets: list[int],
        action: str,
        check_target: bool = True,
    ) -> GoalOut:
        today = self.today()
        errors = goal_errors(
            target_date=target_date if check_target else None, weekday_budgets=budgets, today=today
        )
        if errors:
            raise _validation([(e.field, e.message) for e in errors])
        for old in self._repo.open_goals():
            old.valid_to = max(today, old.valid_from)  # close; a same-day change leaves an empty range
        goal = Goal(
            role_profile_id=profile.id,
            target_date=target_date,
            weekday_budgets_json=list(budgets),
            valid_from=today,
            valid_to=None,
            created_at=self._clock.now_utc().astimezone(UTC).replace(tzinfo=None),
        )
        self._repo.add_goal(goal)
        self._audit(
            "goal",
            str(goal.id),
            action,
            {"profile_key": profile.profile_key, "target_date": str(target_date), "weekday_budgets": budgets},
        )
        self._s.commit()
        return self._out(goal)

    def create_goal(self, payload: GoalInput) -> GoalOut:
        current = self._repo.goal_on(self.today())
        profile = self._profile(payload.profile_key, current.role_profile_id if current else None)
        default = profile.config_json.get("weekday_budgets_default", DEFAULT_WEEKDAY_BUDGETS)
        budgets = payload.weekday_budgets or [int(x) for x in cast(list[int], default)]
        return self._new_version(
            profile=profile, target_date=payload.target_date, budgets=budgets, action="CREATE_GOAL"
        )

    def patch_goal(self, payload: GoalPatch) -> GoalOut:
        current = self._repo.goal_on(self.today())
        if current is None:
            raise AppError(ErrorCode.NOT_FOUND, "No active goal; create one with POST /goals.", 404)
        profile = self._profile(payload.profile_key, current.role_profile_id)
        target = None if payload.clear_target_date else (payload.target_date or current.target_date)
        budgets = payload.weekday_budgets or list(current.weekday_budgets_json)
        return self._new_version(
            profile=profile,
            target_date=target,
            budgets=budgets,
            action="CHANGE_GOAL",
            check_target=payload.target_date is not None,  # an unchanged (possibly past) date stays valid
        )
