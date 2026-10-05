"""Raw activity access. Inserts only (never UPDATE/DELETE on observations).

"Current" attempt = a row that no other row supersedes. Listings are always explicitly ordered.
The skill query (``attempts(skill_key=...)``) is the access path the evidence engine will use:
problem_skills(skill_id) → problem_attempts(problem_id, attempted_on), both indexed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.domain.activity.vocabulary import PERSONAL_PROBLEM_ID_START, PERSONAL_SEED_VERSION
from app.models import AppSettings, AttemptMistake, Problem, ProblemAttempt, ProblemSkill, Skill


@dataclass(frozen=True)
class AttemptRow:
    attempt: ProblemAttempt
    problem: Problem
    mistakes: tuple[str, ...]
    superseded_by_id: int | None
    skill_mapping_bp: int | None = None


@dataclass(frozen=True)
class ProblemStats:
    problem: Problem
    attempt_count: int
    last_attempt: ProblemAttempt | None


class ActivityRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    # ------------------------------------------------------------------ settings
    def timezone(self) -> str | None:
        row = self._s.get(AppSettings, 1)
        return row.timezone if row else None

    # ------------------------------------------------------------------ problems
    def problem(self, problem_id: int) -> Problem | None:
        return self._s.get(Problem, problem_id)

    def problem_by_key(self, platform: str, platform_key: str) -> Problem | None:
        return self._s.scalar(
            select(Problem).where(Problem.platform == platform, Problem.platform_key == platform_key)
        )

    def next_personal_problem_id(self) -> int:
        current = self._s.scalar(select(func.max(Problem.id)).where(Problem.id >= PERSONAL_PROBLEM_ID_START))
        return (current or PERSONAL_PROBLEM_ID_START - 1) + 1

    def add_problem(self, problem: Problem, skills: Sequence[tuple[int, int]]) -> None:
        self._s.add(problem)
        self._s.flush()
        for skill_id, weight in skills:
            self._s.add(ProblemSkill(problem_id=problem.id, skill_id=skill_id, mapping_weight_bp=weight))

    def active_skill_ids(self, keys: Sequence[str]) -> dict[str, int]:
        rows = self._s.execute(
            select(Skill.skill_key, Skill.id).where(Skill.skill_key.in_(keys), Skill.active.is_(True))
        ).all()
        return {key: skill_id for key, skill_id in rows}

    def problems_with_stats(
        self,
        *,
        query: str | None = None,
        difficulty: str | None = None,
        skill_key: str | None = None,
        source: str | None = None,
        problem_id: int | None = None,
    ) -> list[ProblemStats]:
        stmt = select(Problem).where(Problem.active.is_(True))
        if problem_id is not None:
            stmt = stmt.where(Problem.id == problem_id)
        if difficulty is not None:
            stmt = stmt.where(Problem.difficulty == difficulty)
        if source == "PERSONAL":
            stmt = stmt.where(Problem.seed_version == PERSONAL_SEED_VERSION)
        elif source == "CATALOG":
            stmt = stmt.where(Problem.seed_version != PERSONAL_SEED_VERSION)
        if query:
            like = f"%{query.lower()}%"
            stmt = stmt.where(or_(func.lower(Problem.title).like(like), Problem.platform_key.like(like)))
        if skill_key is not None:
            stmt = stmt.where(
                Problem.id.in_(
                    select(ProblemSkill.problem_id)
                    .join(Skill, ProblemSkill.skill_id == Skill.id)
                    .where(Skill.skill_key == skill_key)
                )
            )
        problems = list(self._s.scalars(stmt.order_by(Problem.id)).all())
        ids = [p.id for p in problems]
        counts: dict[int, int] = {}
        last: dict[int, ProblemAttempt] = {}
        if ids:
            current = self._current_attempts().where(ProblemAttempt.problem_id.in_(ids))
            for attempt in self._s.scalars(
                current.order_by(ProblemAttempt.attempted_at.desc(), ProblemAttempt.id.desc())
            ):
                counts[attempt.problem_id] = counts.get(attempt.problem_id, 0) + 1
                last.setdefault(attempt.problem_id, attempt)
        return [ProblemStats(p, counts.get(p.id, 0), last.get(p.id)) for p in problems]

    # ------------------------------------------------------------------ attempts
    def _current_attempts(self) -> Select[tuple[ProblemAttempt]]:
        successor = aliased(ProblemAttempt)
        return (
            select(ProblemAttempt)
            .outerjoin(successor, successor.supersedes_id == ProblemAttempt.id)
            .where(successor.id.is_(None))
        )

    def add_attempt(self, attempt: ProblemAttempt, mistakes: Sequence[str]) -> None:
        self._s.add(attempt)
        self._s.flush()
        for code in sorted(set(mistakes)):
            self._s.add(AttemptMistake(attempt_id=attempt.id, mistake_code=code))

    def attempt_by_client_request(self, client_request_id: str) -> ProblemAttempt | None:
        return self._s.scalar(
            select(ProblemAttempt).where(ProblemAttempt.client_request_id == client_request_id)
        )

    def successor_id(self, attempt_id: int) -> int | None:
        return self._s.scalar(select(ProblemAttempt.id).where(ProblemAttempt.supersedes_id == attempt_id))

    def attempts(
        self,
        *,
        problem_id: int | None = None,
        skill_key: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        outcome: str | None = None,
        include_superseded: bool = False,
        ascending: bool = False,
        limit: int = 100,
        offset: int = 0,
        attempt_id: int | None = None,
    ) -> list[AttemptRow]:
        stmt = select(ProblemAttempt) if include_superseded or attempt_id else self._current_attempts()
        mapping = None
        if skill_key is not None:
            mapping = aliased(ProblemSkill)
            stmt = (
                stmt.add_columns(mapping.mapping_weight_bp)
                .join(mapping, mapping.problem_id == ProblemAttempt.problem_id)
                .join(Skill, and_(Skill.id == mapping.skill_id, Skill.skill_key == skill_key))
            )
        if attempt_id is not None:
            stmt = stmt.where(ProblemAttempt.id == attempt_id)
        if problem_id is not None:
            stmt = stmt.where(ProblemAttempt.problem_id == problem_id)
        if date_from is not None:
            stmt = stmt.where(ProblemAttempt.attempted_on >= date_from)
        if date_to is not None:
            stmt = stmt.where(ProblemAttempt.attempted_on <= date_to)
        if outcome is not None:
            stmt = stmt.where(ProblemAttempt.outcome == outcome)
        if ascending:
            stmt = stmt.order_by(ProblemAttempt.attempted_at, ProblemAttempt.id)
        else:
            stmt = stmt.order_by(ProblemAttempt.attempted_at.desc(), ProblemAttempt.id.desc())
        rows = self._s.execute(stmt.limit(limit).offset(offset)).all()
        attempts = [row[0] for row in rows]
        weights = [row[1] if mapping is not None else None for row in rows]
        return self._hydrate(attempts, weights)

    def _hydrate(self, attempts: Sequence[ProblemAttempt], weights: Sequence[int | None]) -> list[AttemptRow]:
        if not attempts:
            return []
        ids = [a.id for a in attempts]
        mistakes: dict[int, list[str]] = {}
        for attempt_id, code in self._s.execute(
            select(AttemptMistake.attempt_id, AttemptMistake.mistake_code)
            .where(AttemptMistake.attempt_id.in_(ids))
            .order_by(AttemptMistake.attempt_id, AttemptMistake.mistake_code)
        ):
            mistakes.setdefault(attempt_id, []).append(code)
        successor_rows = self._s.execute(
            select(ProblemAttempt.supersedes_id, ProblemAttempt.id).where(
                ProblemAttempt.supersedes_id.in_(ids)
            )
        ).all()
        successors: dict[int, int] = {int(old): int(new) for old, new in successor_rows}
        problems = {
            p.id: p
            for p in self._s.scalars(select(Problem).where(Problem.id.in_({a.problem_id for a in attempts})))
        }
        return [
            AttemptRow(a, problems[a.problem_id], tuple(mistakes.get(a.id, ())), successors.get(a.id), w)
            for a, w in zip(attempts, weights, strict=True)
        ]

    def battery_keys(self) -> set[str]:
        """Battery items with at least one current attempt."""
        sub = self._current_attempts().where(ProblemAttempt.battery_item_key.is_not(None)).subquery()
        return {str(k) for k in self._s.scalars(select(sub.c.battery_item_key).distinct())}

    def counts(self) -> dict[str, int]:
        current = self._current_attempts().subquery()
        outcome_rows = self._s.execute(
            select(current.c.outcome, func.count()).group_by(current.c.outcome)
        ).all()
        by_outcome: dict[str, int] = {str(k): int(v) for k, v in outcome_rows}
        return {
            "attempts_total_rows": int(self._s.scalar(select(func.count()).select_from(ProblemAttempt)) or 0),
            "attempts_current": int(sum(by_outcome.values())),
            **{f"attempts_{k.lower()}": int(v) for k, v in sorted(by_outcome.items())},
        }
