"""Assessment capture (quizzes, explanations, designs, rehearsals, study, self-assessment). Raw only.

Every write is one transaction: the assessment row(s) + one audit_log row per created assessment.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.activity.rules import AssessmentSkillFact, assessment_errors
from app.domain.clock import Clock, local_date
from app.errors import AppError
from app.models import Assessment, AssessmentSkill, AuditLog, Skill
from app.repositories.activity_repository import ActivityRepository
from app.repositories.assessment_repository import AssessmentRepository, AssessmentRow
from app.schemas.assessment import (
    AssessmentInput,
    AssessmentOut,
    AssessmentSkillOut,
    SelfAssessmentSweepInput,
)
from app.schemas.envelope import ErrorCode
from app.services.activity_service import FALLBACK_TIMEZONE, _naive_utc, _validation, link_key_errors

SWEEP_BATTERY_ITEM = "M0-B01"
SWEEP_SOURCE_KEY = "battery:M0-B01"


class AssessmentService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._repo = AssessmentRepository(session)
        self._clock = clock

    def _skills(self, keys: list[str]) -> dict[str, Skill]:
        rows = self._s.scalars(select(Skill).where(Skill.skill_key.in_(keys), Skill.active.is_(True)))
        return {s.skill_key: s for s in rows}

    def _build(
        self, payload: AssessmentInput, *, supersedes_id: int | None
    ) -> tuple[Assessment, list[AssessmentSkill]]:
        now = self._clock.now_utc()
        observed_at = payload.observed_at or now
        skills = self._skills([s.skill for s in payload.skills])
        errors = assessment_errors(
            kind=payload.kind,
            observed_at=observed_at,
            now_utc=now,
            timed=payload.timed,
            time_seconds=payload.time_seconds,
            time_limit_seconds=payload.time_limit_seconds,
            familiarity=payload.familiarity,
            study_minutes=payload.study_minutes,
            skills=tuple(
                AssessmentSkillFact(
                    s.skill, skills[s.skill].component if s.skill in skills else None, s.outcome_points
                )
                for s in payload.skills
            ),
        )
        link_errors = link_key_errors(
            self._s, payload.revision_item_key, payload.battery_item_key, problem_id=None
        )
        if errors or link_errors:
            raise _validation([(e.field, e.message) for e in errors] + link_errors)
        tz = ActivityRepository(self._s).timezone() or FALLBACK_TIMEZONE
        assessment = Assessment(
            kind=payload.kind,
            observed_on=local_date(observed_at, tz),
            observed_at=_naive_utc(observed_at),
            mode=payload.mode,
            source_key=payload.source_key,
            notes_used=payload.notes_used,
            reference_used=payload.reference_used,
            hints_used=payload.hints_used,
            timed=payload.timed,
            time_limit_seconds=payload.time_limit_seconds,
            time_seconds=payload.time_seconds,
            peer_evaluated=payload.peer_evaluated,
            applied=payload.applied,
            unseen_variant=payload.unseen_variant,
            difficulty=payload.difficulty,
            followup_points=payload.followup_points,
            communication_points=payload.communication_points,
            rubric_json=payload.rubric,
            familiarity=payload.familiarity,
            study_minutes=payload.study_minutes,
            self_rating_before=payload.self_rating_before,
            self_rating_after=payload.self_rating_after,
            notes=payload.notes,
            revision_item_key=payload.revision_item_key,
            battery_item_key=payload.battery_item_key,
            client_request_id=payload.client_request_id,
            supersedes_id=supersedes_id,
            created_at=_naive_utc(now),
        )
        links = [
            AssessmentSkill(
                skill_id=skills[s.skill].id,
                outcome_points=s.outcome_points,
                mapping_weight_bp=s.mapping_weight_bp,
                is_pattern_target=s.is_pattern_target,
            )
            for s in payload.skills
        ]
        return assessment, links

    def _check_duplicate(self, client_request_id: str | None) -> None:
        if client_request_id and (dup := self._repo.by_client_request(client_request_id)):
            raise AppError(
                ErrorCode.CONFLICT, "This assessment was already recorded.", 409, {"assessment_id": dup.id}
            )

    def record(self, payload: AssessmentInput, *, plan_item_id: int | None = None) -> AssessmentOut:
        self._check_duplicate(payload.client_request_id)
        assessment, links = self._build(payload, supersedes_id=None)
        assessment.plan_item_id = plan_item_id
        self._repo.add(assessment, links)
        self._audit(assessment, "CREATE_ASSESSMENT", payload.model_dump(mode="json"))
        self._commit()
        return self.get(assessment.id)

    def correct(self, assessment_id: int, payload: AssessmentInput) -> AssessmentOut:
        """Append a corrected version; the original row is never modified."""
        original = self._repo.find(assessment_id=assessment_id, include_superseded=True)
        if not original:
            raise AppError(ErrorCode.NOT_FOUND, f"Assessment {assessment_id} not found.", 404)
        if original[0].superseded_by_id is not None:
            raise AppError(
                ErrorCode.INVALID_STATE,
                "This assessment was already corrected; correct its latest version instead.",
                409,
                {"latest_assessment_id": self._latest(assessment_id)},
            )
        assessment, links = self._build(payload, supersedes_id=assessment_id)
        self._repo.add(assessment, links)
        self._audit(
            assessment,
            "CORRECT_ASSESSMENT",
            {"supersedes_id": assessment_id, "input": payload.model_dump(mode="json")},
        )
        self._commit()
        return self.get(assessment.id)

    def sweep(self, payload: SelfAssessmentSweepInput) -> list[AssessmentOut]:
        """Battery item M0-B01: one SELF_ASSESSMENT per skill, all in one transaction."""
        keys = [e.skill for e in payload.entries]
        if len(set(keys)) != len(keys):
            raise _validation([("entries", "each skill may appear only once")])
        if payload.client_request_id:
            self._check_duplicate(f"{payload.client_request_id}-0")
        created: list[Assessment] = []
        for index, entry in enumerate(payload.entries):
            item = AssessmentInput(
                kind="SELF_ASSESSMENT",
                observed_at=payload.observed_at,
                mode="BASELINE",
                source_key=SWEEP_SOURCE_KEY,
                familiarity=entry.familiarity,
                skills=[{"skill": entry.skill}],
                battery_item_key=SWEEP_BATTERY_ITEM,
                client_request_id=f"{payload.client_request_id}-{index}"
                if payload.client_request_id
                else None,
            )
            assessment, links = self._build(item, supersedes_id=None)
            self._repo.add(assessment, links)
            self._audit(assessment, "CREATE_ASSESSMENT", item.model_dump(mode="json"))
            created.append(assessment)
        self._commit()
        rows = self._repo.find(assessment_ids=[a.id for a in created], ascending=True, limit=None)
        return [_out(row) for row in rows]

    def _latest(self, assessment_id: int) -> int:
        current = assessment_id
        while (nxt := self._repo.successor_id(current)) is not None:
            current = nxt
        return current

    def get(self, assessment_id: int) -> AssessmentOut:
        rows = self._repo.find(assessment_id=assessment_id, include_superseded=True)
        if not rows:
            raise AppError(ErrorCode.NOT_FOUND, f"Assessment {assessment_id} not found.", 404)
        return _out(rows[0])

    def list_assessments(self, **filters: Any) -> list[AssessmentOut]:
        return [_out(r) for r in self._repo.find(**filters)]

    def _audit(self, assessment: Assessment, action: str, payload: dict[str, Any]) -> None:
        self._s.add(
            AuditLog(
                at=assessment.created_at,
                entity_type="assessment",
                entity_id=str(assessment.id),
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


def _out(row: AssessmentRow) -> AssessmentOut:
    a = row.assessment
    return AssessmentOut(
        id=a.id,
        kind=a.kind,
        observed_at=a.observed_at.replace(tzinfo=UTC),
        observed_on=a.observed_on,
        mode=a.mode,
        source_key=a.source_key,
        notes_used=a.notes_used,
        reference_used=a.reference_used,
        hints_used=a.hints_used,
        timed=a.timed,
        time_limit_seconds=a.time_limit_seconds,
        time_seconds=a.time_seconds,
        peer_evaluated=a.peer_evaluated,
        applied=a.applied,
        unseen_variant=a.unseen_variant,
        difficulty=a.difficulty,
        followup_points=a.followup_points,
        communication_points=a.communication_points,
        rubric=a.rubric_json,
        familiarity=a.familiarity,
        study_minutes=a.study_minutes,
        skills=[
            AssessmentSkillOut(
                skill=s.skill,
                outcome_points=s.outcome_points,
                mapping_weight_bp=s.mapping_weight_bp,
                is_pattern_target=s.is_pattern_target,
            )
            for s in row.skills
        ],
        self_rating_before=a.self_rating_before,
        self_rating_after=a.self_rating_after,
        notes=a.notes,
        revision_item_key=a.revision_item_key,
        battery_item_key=a.battery_item_key,
        supersedes_id=a.supersedes_id,
        superseded_by_id=row.superseded_by_id,
        is_current=row.superseded_by_id is None,
        created_at=a.created_at.replace(tzinfo=UTC),
    )
