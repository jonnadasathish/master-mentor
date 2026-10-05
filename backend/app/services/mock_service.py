"""Mock interview capture (raw, append-only; corrections supersede) and the Mocks page summary."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.domain.clock import Clock, local_date
from app.domain.readiness.engine import final_simulation_failure, is_valid_final_simulation
from app.errors import AppError
from app.models import AuditLog, Mock, MockRoundRow, MockRoundSkill, Skill
from app.repositories.activity_repository import ActivityRepository
from app.schemas.envelope import ErrorCode
from app.schemas.mock import MockInput, MockOut, MockRoundOut, MockRoundSkillIn
from app.services.activity_service import FALLBACK_TIMEZONE, _naive_utc, _validation
from app.services.mentor_service import MentorService

ROUND_COMPONENTS = {
    "DSA": ("dsa", "coding"),
    "CS": ("cs",),
    "LLD": ("lld",),
    "SYSTEM_DESIGN": ("system_design",),
    "BEHAVIORAL": ("behavioral",),
    "PROJECT_DEEP_DIVE": ("project",),
}


class MockService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock

    # ------------------------------------------------------------------ capture
    def _validate(self, payload: MockInput) -> dict[str, Skill]:
        keys = [s.skill for r in payload.rounds for s in r.skills]
        skills = {
            s.skill_key: s
            for s in self._s.scalars(select(Skill).where(Skill.skill_key.in_(keys), Skill.active.is_(True)))
        }
        errors: list[tuple[str, str]] = []
        now = self._clock.now_utc()
        if payload.occurred_at is not None and payload.occurred_at > now:
            errors.append(("occurred_at", "cannot be in the future"))
        for n, r in enumerate(payload.rounds):
            seen: set[str] = set()
            for s in r.skills:
                skill = skills.get(s.skill)
                if skill is None:
                    errors.append((f"rounds[{n}].skills", f"unknown or inactive skill {s.skill!r}"))
                elif skill.component not in ROUND_COMPONENTS[r.round_type]:
                    errors.append(
                        (
                            f"rounds[{n}].skills",
                            f"{r.round_type} round cannot score {skill.component} skill {s.skill!r}",
                        )
                    )
                if s.skill in seen:
                    errors.append((f"rounds[{n}].skills", f"skill {s.skill!r} listed twice"))
                seen.add(s.skill)
        if errors:
            raise _validation(errors)
        return skills

    def _write(self, payload: MockInput, supersedes_id: int | None, plan_item_id: int | None = None) -> Mock:
        skills = self._validate(payload)
        now = self._clock.now_utc()
        occurred = payload.occurred_at or now
        tz = ActivityRepository(self._s).timezone() or FALLBACK_TIMEZONE
        mock = Mock(
            occurred_on=local_date(occurred, tz),
            occurred_at=_naive_utc(occurred),
            source=payload.source,
            is_final_simulation=payload.is_final_simulation,
            notes=payload.notes,
            plan_item_id=plan_item_id,
            client_request_id=payload.client_request_id,
            supersedes_id=supersedes_id,
            created_at=_naive_utc(now),
        )
        self._s.add(mock)
        self._s.flush()
        for position, r in enumerate(payload.rounds, start=1):
            row = MockRoundRow(
                mock_id=mock.id,
                position=position,
                round_type=r.round_type,
                duration_minutes=r.duration_minutes,
                round_score=r.round_score,
                communication_points=r.communication_points,
                rubric_json=r.rubric,
            )
            self._s.add(row)
            self._s.flush()
            for s in r.skills:
                self._s.add(
                    MockRoundSkill(
                        round_id=row.id,
                        skill_id=skills[s.skill].id,
                        outcome_points=s.outcome_points,
                        is_weakness=s.is_weakness,
                    )
                )
        return mock

    def _audit(self, mock: Mock, action: str, payload: dict[str, Any]) -> None:
        self._s.add(
            AuditLog(
                at=mock.created_at,
                entity_type="mock",
                entity_id=str(mock.id),
                action=action,
                payload_json=payload,
            )
        )

    def _commit(self) -> None:
        try:
            self._s.commit()
        except IntegrityError as exc:
            self._s.rollback()
            raise AppError(ErrorCode.CONFLICT, "The record conflicts with existing data.", 409) from exc

    def record(self, payload: MockInput, *, plan_item_id: int | None = None) -> MockOut:
        if payload.client_request_id and (
            dup := self._s.scalar(select(Mock).where(Mock.client_request_id == payload.client_request_id))
        ):
            raise AppError(ErrorCode.CONFLICT, "This mock was already recorded.", 409, {"mock_id": dup.id})
        mock = self._write(payload, None, plan_item_id)
        self._audit(mock, "CREATE_MOCK", payload.model_dump(mode="json"))
        self._commit()
        return self.get(mock.id)

    def correct(self, mock_id: int, payload: MockInput) -> MockOut:
        original = self._s.get(Mock, mock_id)
        if original is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Mock {mock_id} not found.", 404)
        successor = self._s.scalar(select(Mock.id).where(Mock.supersedes_id == mock_id))
        if successor is not None:
            raise AppError(
                ErrorCode.INVALID_STATE,
                "This mock was already corrected; correct its latest version.",
                409,
                {"latest_mock_id": successor},
            )
        mock = self._write(payload, mock_id)
        self._audit(
            mock, "CORRECT_MOCK", {"supersedes_id": mock_id, "input": payload.model_dump(mode="json")}
        )
        self._commit()
        return self.get(mock.id)

    # ------------------------------------------------------------------ reads
    def _outs(self, mocks: Sequence[Mock]) -> list[MockOut]:
        if not mocks:
            return []
        ids = [m.id for m in mocks]
        rounds = list(
            self._s.scalars(
                select(MockRoundRow).where(MockRoundRow.mock_id.in_(ids)).order_by(MockRoundRow.position)
            )
        )
        skills: dict[int, list[MockRoundSkillIn]] = {}
        if rounds:
            for link, key in self._s.execute(
                select(MockRoundSkill, Skill.skill_key)
                .join(Skill, Skill.id == MockRoundSkill.skill_id)
                .where(MockRoundSkill.round_id.in_([r.id for r in rounds]))
                .order_by(Skill.skill_key)
            ).all():
                skills.setdefault(link.round_id, []).append(
                    MockRoundSkillIn(
                        skill=key, outcome_points=link.outcome_points, is_weakness=link.is_weakness
                    )
                )
        successors = {
            int(old): int(new)
            for old, new in self._s.execute(
                select(Mock.supersedes_id, Mock.id).where(Mock.supersedes_id.in_(ids))
            ).all()
        }
        out = []
        for m in mocks:
            out.append(
                MockOut(
                    id=m.id,
                    occurred_on=m.occurred_on,
                    occurred_at=m.occurred_at.replace(tzinfo=UTC),
                    source=m.source,
                    is_final_simulation=m.is_final_simulation,
                    notes=m.notes,
                    rounds=[
                        MockRoundOut(
                            id=r.id,
                            position=r.position,
                            round_type=r.round_type,
                            duration_minutes=r.duration_minutes,
                            round_score=r.round_score,
                            communication_points=r.communication_points,
                            rubric=r.rubric_json,
                            skills=skills.get(r.id, []),
                        )
                        for r in rounds
                        if r.mock_id == m.id
                    ],
                    supersedes_id=m.supersedes_id,
                    superseded_by_id=successors.get(m.id),
                    is_current=m.id not in successors,
                )
            )
        return out

    def get(self, mock_id: int) -> MockOut:
        mock = self._s.get(Mock, mock_id)
        if mock is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Mock {mock_id} not found.", 404)
        return self._outs([mock])[0]

    def list_mocks(self, *, include_superseded: bool = False, limit: int = 100) -> list[MockOut]:
        stmt = select(Mock)
        if not include_superseded:
            successor = aliased(Mock)
            stmt = stmt.outerjoin(successor, successor.supersedes_id == Mock.id).where(successor.id.is_(None))
        mocks = list(self._s.scalars(stmt.order_by(Mock.occurred_at.desc(), Mock.id.desc()).limit(limit)))
        return self._outs(mocks)

    def summary(self) -> dict[str, Any]:
        """Mocks page (UI_SPEC §7): per-type trend + G6, repeated weaknesses, final simulations + G9."""
        mentor = MentorService(self._s, self._clock)
        as_of = mentor.as_of_date()
        result = mentor.evaluate(as_of)
        ctx, out = result.context, result.outputs
        if ctx is None or out is None or out.readiness is None:
            raise AppError(ErrorCode.INVALID_STATE, "No catalog is loaded; run make seed.", 409)
        params = ctx.profile.gate_parameters
        window = int(str(params.get("G6_mock_window_days", 60)))
        rounds = sorted(ctx.readiness_rounds, key=lambda r: (r.occurred_on, r.order, r.id), reverse=True)
        g6 = [c for c in out.readiness.all_failing if c.gate == "G6"]
        mins: dict[str, int] = dict(params.get("G6_min_rounds_per_type", {}))  # type: ignore[call-overload]
        by_type = []
        for rt in ctx.profile.round_types:
            mine = [r for r in rounds if r.round_type == rt]
            recent = [r for r in mine if 0 <= (as_of - r.occurred_on).days <= window]
            failing = [c.message for c in g6 if c.subject.split(":")[0] == rt]
            by_type.append(
                {
                    "round_type": rt,
                    "rounds_60d": len(recent),
                    "required_60d": mins.get(rt, 0),
                    "non_self_60d": sum(1 for r in recent if r.source != "SELF"),
                    "latest": {"date": mine[0].occurred_on.isoformat(), "score": mine[0].score}
                    if mine
                    else None,
                    "trend": [
                        {"date": r.occurred_on.isoformat(), "score": r.score} for r in reversed(mine[:10])
                    ],
                    "g6_failing": failing,
                }
            )
        flagged: dict[str, int] = {}
        for f in ctx.mock_rounds:
            for skill in f.weakness_skills:
                flagged[skill] = flagged.get(skill, 0) + 1
        finals = []
        for sim in sorted(ctx.final_simulations, key=lambda s: (s.occurred_on, s.mock_id), reverse=True):
            valid = is_valid_final_simulation(sim, ctx.profile.final_simulation)
            failure = final_simulation_failure(sim, params) if valid else "composition incomplete"
            finals.append(
                {
                    "mock_id": sim.mock_id,
                    "date": sim.occurred_on.isoformat(),
                    "source": sim.source,
                    "valid": valid,
                    "passed": valid and failure is None,
                    "failure": failure,
                }
            )
        g9 = [c.message for c in out.readiness.all_failing if c.gate == "G9"]
        return {
            "as_of_date": as_of.isoformat(),
            "by_type": by_type,
            "g6_passed": not g6,
            "last_6_mean_failing": [
                c.message for c in g6 if c.subject in ("last_6_mean",) or c.subject.startswith("round:")
            ],
            "repeated_weaknesses": sorted(
                ([k, n] for k, n in flagged.items() if n >= 2), key=lambda x: (-int(x[1]), str(x[0]))
            ),
            "final_simulations": finals,
            "g9_passed": not g9,
            "g9_failing": g9,
            "simulation_eligible": out.readiness.simulation_eligible,
        }
