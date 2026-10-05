"""Raw assessment access. Inserts only; "current" = not superseded (same rule as problem attempts)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, aliased

from app.models import Assessment, AssessmentSkill, Skill


@dataclass(frozen=True)
class AssessmentSkillRow:
    skill: str
    component: str
    is_pattern: bool
    outcome_points: int | None
    mapping_weight_bp: int
    is_pattern_target: bool


@dataclass(frozen=True)
class AssessmentRow:
    assessment: Assessment
    skills: tuple[AssessmentSkillRow, ...]
    superseded_by_id: int | None


class AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _current(self) -> Select[tuple[Assessment]]:
        successor = aliased(Assessment)
        return (
            select(Assessment)
            .outerjoin(successor, successor.supersedes_id == Assessment.id)
            .where(successor.id.is_(None))
        )

    def add(self, assessment: Assessment, skills: Sequence[AssessmentSkill]) -> None:
        self._s.add(assessment)
        self._s.flush()
        for row in skills:
            row.assessment_id = assessment.id
            self._s.add(row)
        self._s.flush()

    def by_client_request(self, client_request_id: str) -> Assessment | None:
        return self._s.scalar(select(Assessment).where(Assessment.client_request_id == client_request_id))

    def successor_id(self, assessment_id: int) -> int | None:
        return self._s.scalar(select(Assessment.id).where(Assessment.supersedes_id == assessment_id))

    def find(
        self,
        *,
        assessment_id: int | None = None,
        assessment_ids: Sequence[int] | None = None,
        kind: str | None = None,
        skill_key: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        include_superseded: bool = False,
        ascending: bool = False,
        limit: int | None = 100,
        offset: int = 0,
    ) -> list[AssessmentRow]:
        explicit = assessment_id is not None or assessment_ids is not None
        stmt = select(Assessment) if include_superseded or explicit else self._current()
        if assessment_id is not None:
            stmt = stmt.where(Assessment.id == assessment_id)
        if assessment_ids is not None:
            stmt = stmt.where(Assessment.id.in_(assessment_ids))
        if kind is not None:
            stmt = stmt.where(Assessment.kind == kind)
        if skill_key is not None:
            stmt = stmt.where(
                Assessment.id.in_(
                    select(AssessmentSkill.assessment_id)
                    .join(Skill, Skill.id == AssessmentSkill.skill_id)
                    .where(Skill.skill_key == skill_key)
                )
            )
        if date_from is not None:
            stmt = stmt.where(Assessment.observed_on >= date_from)
        if date_to is not None:
            stmt = stmt.where(Assessment.observed_on <= date_to)
        if ascending:
            stmt = stmt.order_by(Assessment.observed_at, Assessment.id)
        else:
            stmt = stmt.order_by(Assessment.observed_at.desc(), Assessment.id.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = list(self._s.scalars(stmt.offset(offset)).all())
        return self._hydrate(rows)

    def _hydrate(self, assessments: Sequence[Assessment]) -> list[AssessmentRow]:
        if not assessments:
            return []
        ids = [a.id for a in assessments]
        skills: dict[int, list[AssessmentSkillRow]] = {}
        for link, skill in self._s.execute(
            select(AssessmentSkill, Skill)
            .join(Skill, Skill.id == AssessmentSkill.skill_id)
            .where(AssessmentSkill.assessment_id.in_(ids))
            .order_by(AssessmentSkill.assessment_id, Skill.skill_key)
        ).all():
            skills.setdefault(link.assessment_id, []).append(
                AssessmentSkillRow(
                    skill.skill_key,
                    skill.component,
                    skill.is_pattern,
                    link.outcome_points,
                    link.mapping_weight_bp,
                    link.is_pattern_target,
                )
            )
        successors = {
            int(old): int(new)
            for old, new in self._s.execute(
                select(Assessment.supersedes_id, Assessment.id).where(Assessment.supersedes_id.in_(ids))
            ).all()
        }
        return [AssessmentRow(a, tuple(skills.get(a.id, ())), successors.get(a.id)) for a in assessments]

    def battery_keys(self) -> set[str]:
        """Battery items with at least one current observation (assessment side)."""
        sub = self._current().where(Assessment.battery_item_key.is_not(None)).subquery()
        return {str(k) for k in self._s.scalars(select(sub.c.battery_item_key).distinct())}
