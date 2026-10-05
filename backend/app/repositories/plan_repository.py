"""Daily plans and plan items (decision history). Plans are written once; items only change status."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyPlanRow, PlanItemRow, Skill


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def plan_on(self, day: date) -> DailyPlanRow | None:
        return self._s.scalar(select(DailyPlanRow).where(DailyPlanRow.plan_date == day))

    def items(self, plan_id: int) -> list[tuple[PlanItemRow, str | None]]:
        rows = self._s.execute(
            select(PlanItemRow, Skill.skill_key)
            .outerjoin(Skill, Skill.id == PlanItemRow.skill_id)
            .where(PlanItemRow.plan_id == plan_id)
            .order_by(PlanItemRow.position)
        ).all()
        return [(r[0], r[1]) for r in rows]

    def item(self, item_id: int) -> PlanItemRow | None:
        return self._s.get(PlanItemRow, item_id)

    def history(self, as_of: date, days: int = 14) -> list[tuple[PlanItemRow, DailyPlanRow, str | None]]:
        rows = self._s.execute(
            select(PlanItemRow, DailyPlanRow, Skill.skill_key)
            .join(DailyPlanRow, DailyPlanRow.id == PlanItemRow.plan_id)
            .outerjoin(Skill, Skill.id == PlanItemRow.skill_id)
            .where(DailyPlanRow.plan_date >= as_of - timedelta(days=days), DailyPlanRow.plan_date < as_of)
            .order_by(DailyPlanRow.plan_date, PlanItemRow.position)
        ).all()
        return [(r[0], r[1], r[2]) for r in rows]

    def done_battery_keys(self) -> set[str]:
        stmt = select(PlanItemRow.battery_item_key).where(
            PlanItemRow.status == "DONE", PlanItemRow.battery_item_key.is_not(None)
        )
        return {str(k) for k in self._s.scalars(stmt)}

    def item_minutes(self, ids: Sequence[int]) -> dict[int, int]:
        if not ids:
            return {}
        return {
            i: m
            for i, m in self._s.execute(
                select(PlanItemRow.id, PlanItemRow.minutes).where(PlanItemRow.id.in_(ids))
            )
        }
