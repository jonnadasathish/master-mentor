"""Roadmap read model (UI_SPEC §5 Roadmap tab): tracks x milestones with completion and the current milestone.

Completion rules are the mentor's own (app.domain.mentor.roadmap); nothing is recomputed in the UI.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.domain.mentor.roadmap import EXTRA_EXIT, MILESTONE_EXIT_LEVEL, current_milestones, milestone_complete
from app.errors import AppError
from app.schemas.envelope import ErrorCode
from app.services.plan_service import PlanService


class RoadmapService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._plans = PlanService(session, clock)
        self._mentor = self._plans.mentor

    def roadmap(self) -> dict[str, Any]:
        as_of = self._mentor.as_of_date()
        result = self._mentor.evaluate(as_of)
        out, ctx, cal = result.outputs, result.context, result.calibration
        if out is None or ctx is None or cal is None:
            raise AppError(ErrorCode.INVALID_STATE, "No catalog is loaded; run make seed.", 409)
        milestones = self._plans.milestones()
        facts = self._plans.exit_facts()
        current = current_milestones(milestones, out.states, ctx.graph, facts)
        tracks: dict[str, dict[str, Any]] = {}
        for m in sorted(milestones, key=lambda x: (x.track_position, x.position)):
            cur = current.get(m.track)
            track = tracks.setdefault(
                m.track,
                {
                    "track": m.track,
                    "current_milestone": cur.key if cur else None,
                    "milestones": [],
                },
            )
            skills = []
            for key in m.skills:
                spec = ctx.graph.skills.get(key)
                state = out.states.get(key)
                level = state.level if state is not None else None
                skills.append(
                    {
                        "key": key,
                        "required": bool(spec and spec.required),
                        "level": level,
                        "done": state is not None and state.assessed and (level or 0) >= MILESTONE_EXIT_LEVEL,
                    }
                )
            required = [s for s in skills if s["required"]]
            track["milestones"].append(
                {
                    "key": m.key,
                    "name": m.name,
                    "position": m.position,
                    "content": m.content,
                    "skills": skills,
                    "required_total": len(required),
                    "required_done": sum(1 for s in required if s["done"]),
                    "extra_exit": [
                        {"text": t, "met": t in EXTRA_EXIT and EXTRA_EXIT[t](m, out.states, ctx.graph, facts)}
                        for t in m.extra_exit
                    ],
                    "complete": milestone_complete(m, out.states, ctx.graph, facts),
                    "current": cur is not None and cur.key == m.key,
                }
            )
        return {
            "as_of_date": as_of.isoformat(),
            "tracks": list(tracks.values()),
            "baseline": {
                "done": cal.battery_done,
                "total": cal.battery_total,
                "next_item": cal.next_item,
                "calibration_mode": cal.calibration_mode,
            },
        }
