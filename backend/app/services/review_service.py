"""Weekly reviews (MENTOR_ENGINE §10): generated lazily for a completed week, then stored once."""

from __future__ import annotations

from datetime import UTC, date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.domain.mentor.practice import summarize_practice
from app.domain.review.weekly import (
    WeekMockRound,
    WeekPlanItem,
    WeekPoint,
    generate_weekly_review,
    last_completed_week,
)
from app.domain.revision.engine import backlog_minutes
from app.domain.rulesets import get_ruleset
from app.errors import AppError
from app.models import AuditLog, DailyPlanRow, PlanItemRow, WeeklyReviewRow
from app.schemas.envelope import ErrorCode
from app.schemas.review import ReflectionIn, WeeklyReviewOut
from app.services.activity_service import _naive_utc
from app.services.mentor_service import MentorService, RunResult
from app.services.plan_service import PlanService


class ReviewService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock
        self._mentor = MentorService(session, clock)
        self._ruleset = get_ruleset(self._mentor.ruleset_version)

    @staticmethod
    def _out(row: WeeklyReviewRow) -> WeeklyReviewOut:
        return WeeklyReviewOut(
            id=row.id,
            week_start=row.week_start,
            run_id=row.run_id,
            ruleset_version=row.ruleset_version,
            metrics=dict(row.metrics_json),
            next_focus=dict(row.next_focus_json),
            reflection=dict(row.reflection_json) if row.reflection_json else None,
            generated_at=row.generated_at.replace(tzinfo=UTC),
            reflected_at=row.reflected_at.replace(tzinfo=UTC) if row.reflected_at else None,
        )

    def _row(self, week_start: date) -> WeeklyReviewRow | None:
        return self._s.scalar(select(WeeklyReviewRow).where(WeeklyReviewRow.week_start == week_start))

    def _point(self, result: RunResult) -> WeekPoint:
        out = result.outputs
        if out is None or out.gaps is None or out.readiness is None:
            raise AppError(ErrorCode.INVALID_STATE, "No catalog is loaded; run make seed.", 409)
        parked = out.parked_skills()
        backlog = backlog_minutes(
            out.revision.items if out.revision else {}, parked, result.as_of_date, self._ruleset
        )
        return WeekPoint(result.as_of_date, out.states, out.gaps, out.readiness, backlog)

    def _generate(self, week_start: date) -> WeeklyReviewRow:
        week_end = week_start + timedelta(days=6)
        start_eval = self._mentor.evaluate(week_start - timedelta(days=1))
        end_eval = self._mentor.evaluate(week_end)
        assert end_eval.outputs is not None and end_eval.context is not None
        rows = end_eval.outputs.rows
        active_days = len(
            {r.observed_on for r in rows if r.is_scoring and week_start <= r.observed_on <= week_end}
        )
        items = [
            WeekPlanItem(plan.plan_date, item.candidate_type, item.minutes, item.status)
            for item, plan in self._s.execute(
                select(PlanItemRow, DailyPlanRow)
                .join(DailyPlanRow, DailyPlanRow.id == PlanItemRow.plan_id)
                .where(DailyPlanRow.plan_date >= week_start, DailyPlanRow.plan_date <= week_end)
            ).all()
        ]
        ctx = end_eval.context
        practice = summarize_practice(
            PlanService(self._s, self._clock).practice_observations(),
            week_end + timedelta(days=1),
            ctx.graph,
            ctx.profile,
        )
        mocks = [
            WeekMockRound(r.occurred_on, r.round_type, r.score)
            for r in ctx.readiness_rounds
            if week_start <= r.occurred_on <= week_end
        ]
        metrics, focus = generate_weekly_review(
            week_start=week_start,
            start=self._point(start_eval),
            end=self._point(end_eval),
            active_days=active_days,
            plan_items=items,
            track_minutes=practice.track_minutes_7d,
            mock_rounds=mocks,
            profile=ctx.profile,
        )
        now = _naive_utc(self._clock.now_utc())
        row = WeeklyReviewRow(
            week_start=week_start,
            run_id=end_eval.run_id or None,
            ruleset_version=self._mentor.ruleset_version,
            metrics_json=metrics,
            next_focus_json=focus,
            generated_at=now,
        )
        self._s.add(row)
        self._s.flush()
        self._s.add(
            AuditLog(
                at=now,
                entity_type="weekly_review",
                entity_id=week_start.isoformat(),
                action="GENERATE_WEEKLY_REVIEW",
                payload_json={"week_start": week_start.isoformat()},
            )
        )
        self._s.commit()
        return row

    def get(self, week_start: date) -> WeeklyReviewOut:
        if week_start.weekday() != 0:
            raise AppError(ErrorCode.VALIDATION_ERROR, "week_start must be a Monday.", 422)
        row = self._row(week_start)
        if row is None:
            if week_start + timedelta(days=6) >= self._mentor.as_of_date():
                raise AppError(ErrorCode.INVALID_STATE, "That week has not ended yet.", 409)
            row = self._generate(week_start)
        return self._out(row)

    def latest(self) -> WeeklyReviewOut:
        return self.get(last_completed_week(self._mentor.as_of_date()))

    def list_reviews(self) -> list[WeeklyReviewOut]:
        return [
            self._out(r)
            for r in self._s.scalars(select(WeeklyReviewRow).order_by(WeeklyReviewRow.week_start.desc()))
        ]

    def reflect(self, week_start: date, payload: ReflectionIn) -> WeeklyReviewOut:
        row = self._row(week_start)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND, f"No weekly review for {week_start.isoformat()}.", 404)
        before = dict(row.reflection_json) if row.reflection_json else None
        row.reflection_json = payload.model_dump()
        row.reflected_at = _naive_utc(self._clock.now_utc())
        self._s.add(
            AuditLog(
                at=row.reflected_at,
                entity_type="weekly_review",
                entity_id=week_start.isoformat(),
                action="REFLECT_WEEKLY_REVIEW",
                payload_json={"before": before, "after": payload.model_dump()},
            )
        )
        self._s.commit()
        return self._out(row)
