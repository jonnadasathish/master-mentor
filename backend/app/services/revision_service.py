"""Revision page read model and manual actions. Rules live in app.domain.revision; this only composes."""

from __future__ import annotations

from datetime import UTC, date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.domain.profile.goals import budget_for
from app.domain.revision.engine import revision_cap
from app.domain.rulesets import get_ruleset
from app.errors import AppError
from app.models import AuditLog, GapState, RevisionItemAction, RevisionItemRow, RoleSkillTarget, Skill
from app.repositories.profile_repository import ProfileRepository
from app.schemas.envelope import ErrorCode
from app.schemas.revision import RevisionItemOut, RevisionListOut
from app.services.skill_service import SkillService

BUCKETS = ("overdue", "due", "upcoming", "maintenance", "suspended", "graduated")
REVIEW_KIND = {
    "PROBLEM": "ATTEMPT",
    "PATTERN": "PATTERN_DRILL",
    "CS": "CONCEPT_EXPLAIN",
    "CONCEPT": "CONCEPT_EXPLAIN",
    "SD": "SD_DESIGN",
    "BEHAVIORAL": "STORY_REHEARSAL",
    "MOCK_WEAKNESS": "CONCEPT_EXPLAIN",
}
DEFAULT_BUDGET = 90


def bucket_of(row: RevisionItemRow, today: date) -> str:
    if row.state == "SUSPENDED":
        return "suspended"
    if row.state == "GRADUATED":
        return "maintenance" if row.due_date is not None and row.due_date <= today else "graduated"
    if row.due_date is not None and row.due_date < today:
        return "overdue"
    if row.due_date is not None and row.due_date == today:
        return "due"
    return "upcoming"


class RevisionService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock
        self._skills = SkillService(session, clock)
        self._profiles = ProfileRepository(session)

    @property
    def skills(self) -> SkillService:
        return self._skills

    def _today(self) -> date:
        return self._skills.mentor.as_of_date()

    def item_exists(self, item_key: str) -> bool:
        return self._s.get(RevisionItemRow, item_key) is not None

    def listing(self, bucket: str | None) -> RevisionListOut:
        if bucket is not None and bucket not in BUCKETS:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unknown bucket {bucket!r}", 422)
        today = self._today()
        ruleset = get_ruleset(self._skills.mentor.ruleset_version)
        goal = self._profiles.goal_on(today)
        budget = budget_for(goal.weekday_budgets_json, today) if goal else DEFAULT_BUDGET
        cap = revision_cap(budget, ruleset)
        profile = self._profiles.profile_row(goal.role_profile_id if goal else None)
        targets: dict[int, RoleSkillTarget] = {}
        if profile is not None:
            stmt = select(RoleSkillTarget).where(RoleSkillTarget.profile_id == profile.id)
            targets = {t.skill_id: t for t in self._s.scalars(stmt)}
        parked = {g.skill_id for g in self._s.scalars(select(GapState).where(GapState.status == "PARKED"))}
        extra = int(ruleset.REINFORCE_EXTRA_MINUTES)
        items: list[RevisionItemOut] = []
        backlog = 0
        counts = dict.fromkeys(BUCKETS, 0)
        rows = self._s.execute(
            select(RevisionItemRow, Skill)
            .join(Skill, Skill.id == RevisionItemRow.skill_id)
            .order_by(RevisionItemRow.due_date, RevisionItemRow.item_key)
        ).all()
        for row, skill in rows:
            b = bucket_of(row, today)
            counts[b] += 1
            minutes = row.minutes + (extra if row.needs_reinforcement else 0)
            is_parked = row.skill_id in parked
            if b in ("overdue", "due") and not is_parked:
                backlog += minutes
            if bucket is not None and b != bucket:
                continue
            target = targets.get(row.skill_id)
            items.append(
                RevisionItemOut(
                    item_key=row.item_key,
                    item_type=row.item_type,
                    skill=skill.skill_key,
                    skill_name=skill.name,
                    tier=target.tier if target else None,
                    importance=target.importance if target else None,
                    parked=is_parked,
                    state=row.state,
                    suspend_reason=row.suspend_reason,
                    interval_index=row.interval_index,
                    due_date=row.due_date,
                    days_overdue=max((today - row.due_date).days, 0) if row.due_date else 0,
                    lapses=row.lapses,
                    needs_reinforcement=row.needs_reinforcement,
                    minutes=minutes,
                    bucket=b,
                    review_kind=REVIEW_KIND.get(row.item_type, "CONCEPT_EXPLAIN")
                    if not row.item_key.startswith("PROJECT:")
                    else "PROJECT_WALKTHROUGH",
                    subject_ref=row.subject_ref,
                    last_reviewed_on=row.last_reviewed_on,
                )
            )
        return RevisionListOut(
            backlog_minutes=backlog,
            cap_minutes=cap,
            triage_threshold_minutes=int(ruleset.TRIAGE_TRIGGER_MULTIPLE) * cap,
            counts=counts,
            items=items,
        )

    def manual_action(self, item_key: str, action: str) -> None:
        """Record a MANUAL suspend/resume decision (action row + audit). The caller then runs the engines."""
        row = self._s.get(RevisionItemRow, item_key)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Revision item {item_key!r} not found.", 404)
        if action == "SUSPEND" and row.state != "ACTIVE":
            raise AppError(ErrorCode.INVALID_STATE, f"Only ACTIVE items can be suspended ({row.state}).", 409)
        if action == "RESUME" and row.state != "SUSPENDED":
            raise AppError(
                ErrorCode.INVALID_STATE, f"Only SUSPENDED items can be resumed ({row.state}).", 409
            )
        now = self._clock.now_utc().astimezone(UTC).replace(tzinfo=None)
        today = self._today()
        self._s.add(
            RevisionItemAction(
                item_key=item_key, action=action, reason="MANUAL", action_on=today, created_at=now
            )
        )
        self._s.add(
            AuditLog(
                at=now,
                entity_type="revision_item",
                entity_id=item_key,
                action=f"{action}_REVISION_ITEM",
                payload_json={"reason": "MANUAL", "action_on": today.isoformat()},
            )
        )
        self._s.commit()

    def item(self, item_key: str) -> RevisionItemOut:
        for item in self.listing(None).items:
            if item.item_key == item_key:
                return item
        raise AppError(ErrorCode.NOT_FOUND, f"Revision item {item_key!r} not found.", 404)
