"""Communication Readiness inputs: evidence rows per communication skill, split by how they were recorded."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import Assessment, AssessmentSkill, Skill, SpeakingPractice

NOT_EVIDENCE_KINDS = ("STUDY_SESSION", "SELF_ASSESSMENT")


@dataclass
class SkillEvidenceCounts:
    measured: int = 0  # speaking practices recorded from a browser transcript
    manual: int = 0  # speaking practices recorded by manual self-review
    other: int = 0  # any other scored observation (checks, written practice)
    self_reported: bool = False


class CommunicationRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def evidence_counts(self, skill_keys: Collection[str]) -> dict[str, SkillEvidenceCounts]:
        """Current (not superseded) observations per skill; corrected originals are not counted twice."""
        later = aliased(Assessment)
        rows = self._s.execute(
            select(Skill.skill_key, Assessment.kind, SpeakingPractice.source)
            .join(AssessmentSkill, AssessmentSkill.skill_id == Skill.id)
            .join(Assessment, Assessment.id == AssessmentSkill.assessment_id)
            .outerjoin(SpeakingPractice, SpeakingPractice.assessment_id == Assessment.id)
            .where(
                Skill.skill_key.in_(list(skill_keys)),
                ~select(later.id).where(later.supersedes_id == Assessment.id).exists(),
            )
        ).all()
        out: dict[str, SkillEvidenceCounts] = {}
        for key, kind, source in rows:
            c = out.setdefault(key, SkillEvidenceCounts())
            if kind == "SELF_ASSESSMENT":
                c.self_reported = True
            elif source == "BROWSER":
                c.measured += 1
            elif source == "MANUAL":
                c.manual += 1
            elif kind not in NOT_EVIDENCE_KINDS:
                c.other += 1
        return out

    def history(self, limit: int) -> list[tuple[Assessment, SpeakingPractice, str]]:
        """Newest speaking practices first, each with its primary skill (current rows only)."""
        later = aliased(Assessment)
        rows = self._s.execute(
            select(Assessment, SpeakingPractice, Skill.skill_key)
            .join(SpeakingPractice, SpeakingPractice.assessment_id == Assessment.id)
            .join(AssessmentSkill, AssessmentSkill.assessment_id == Assessment.id)
            .join(Skill, Skill.id == AssessmentSkill.skill_id)
            .where(
                AssessmentSkill.mapping_weight_bp == 10000,
                ~select(later.id).where(later.supersedes_id == Assessment.id).exists(),
            )
            .order_by(Assessment.observed_at.desc(), Assessment.id.desc())
            .limit(limit)
        ).all()
        return [(a, p, k) for a, p, k in rows]
