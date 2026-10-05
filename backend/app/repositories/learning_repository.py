"""Learning data access: the catalog (as the pure LearningCatalog), content observations and sessions."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem, LearningCatalog, Topic, Track
from app.domain.learning.progress import ContentObservation
from app.models import (
    Assessment,
    AssessmentSkill,
    LearningContent,
    LearningContentSkill,
    LearningSession,
    LearningSessionStep,
    LearningTopic,
    LearningTopicSkill,
    LearningTrack,
    Skill,
)


class LearningRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    # ------------------------------------------------------------------------------------------- catalog
    def catalog(self) -> LearningCatalog:
        """The active learning catalog in seed order, rebuilt from the catalog tables."""
        skill_key = {s.id: s.skill_key for s in self._s.scalars(select(Skill))}
        topic_skills: dict[int, list[tuple[int, str]]] = {}
        for row in self._s.scalars(select(LearningTopicSkill)):
            topic_skills.setdefault(row.topic_id, []).append((row.position, skill_key[row.skill_id]))
        topics_by_track: dict[int, list[Topic]] = {}
        tracks_rows = list(self._s.scalars(select(LearningTrack).order_by(LearningTrack.position)))
        track_key = {t.id: t.track_key for t in tracks_rows}
        for t in self._s.scalars(
            select(LearningTopic).order_by(LearningTopic.track_id, LearningTopic.position)
        ):
            skills = tuple(k for _, k in sorted(topic_skills.get(t.id, [])))
            topics_by_track.setdefault(t.track_id, []).append(
                Topic(t.topic_key, track_key[t.track_id], t.position, t.title, t.summary, skills)
            )
        tracks = tuple(
            Track(
                t.track_key,
                t.position,
                t.title,
                t.summary,
                tuple(t.components_json),
                tuple(topics_by_track.get(t.id, [])),
            )
            for t in tracks_rows
        )
        content_skills: dict[int, list[tuple[int, str]]] = {}
        for link in self._s.scalars(select(LearningContentSkill)):
            content_skills.setdefault(link.content_id, []).append((link.position, skill_key[link.skill_id]))
        items = tuple(
            ContentItem(
                key=c.content_key,
                type=c.content_type,
                title=c.title,
                skills=tuple(k for _, k in sorted(content_skills.get(c.id, []))),
                minutes=c.minutes,
                difficulty=c.difficulty,
                stages=tuple(c.stages_json),
                observation_kind=c.observation_kind,
                time_limit_seconds=c.time_limit_seconds,
                problem_ids=tuple(c.problem_ids_json),
                body=c.body_json,
                position=c.position,
                source_file=c.source_file,
            )
            for c in self._s.scalars(
                select(LearningContent)
                .where(LearningContent.active.is_(True))
                .order_by(LearningContent.position)
            )
        )
        return LearningCatalog(tracks, items, {c.key: c for c in items})

    # -------------------------------------------------------------------------------------- observations
    def content_observations(self, content_key: str | None = None) -> list[ContentObservation]:
        """Current (not superseded) assessments recorded from content, with their primary skill's points."""
        successor = aliased(Assessment)
        stmt = (
            select(Assessment, AssessmentSkill.outcome_points)
            .join(AssessmentSkill, AssessmentSkill.assessment_id == Assessment.id)
            .outerjoin(successor, successor.supersedes_id == Assessment.id)
            .where(successor.id.is_(None), Assessment.source_key.like(f"{lv.SOURCE_KEY_PREFIX}%"))
            .where(AssessmentSkill.mapping_weight_bp == 10000)
            .order_by(Assessment.observed_on, Assessment.id)
        )
        if content_key is not None:
            stmt = stmt.where(
                (Assessment.source_key == f"{lv.SOURCE_KEY_PREFIX}{content_key}")
                | Assessment.source_key.like(f"{lv.SOURCE_KEY_PREFIX}{content_key}#%")
            )
        seen: set[int] = set()
        out: list[ContentObservation] = []
        for assessment, points in self._s.execute(stmt):
            if assessment.id in seen:
                continue
            seen.add(assessment.id)
            out.append(
                ContentObservation(assessment.source_key, points, assessment.observed_on, assessment.id)
            )
        return out

    # ------------------------------------------------------------------------------------------ sessions
    def session(self, session_id: int) -> LearningSession | None:
        return self._s.get(LearningSession, session_id)

    def steps(self, session_id: int) -> list[LearningSessionStep]:
        return list(
            self._s.scalars(
                select(LearningSessionStep)
                .where(LearningSessionStep.session_id == session_id)
                .order_by(LearningSessionStep.position)
            )
        )

    def active_session(self, skill_id: int) -> LearningSession | None:
        return self._s.scalar(
            select(LearningSession)
            .where(LearningSession.skill_id == skill_id, LearningSession.status == "ACTIVE")
            .order_by(LearningSession.id.desc())
            .limit(1)
        )

    def session_for_plan_item(self, plan_item_id: int) -> LearningSession | None:
        return self._s.scalar(
            select(LearningSession)
            .where(LearningSession.plan_item_id == plan_item_id)
            .order_by(LearningSession.id.desc())
            .limit(1)
        )

    def sessions(self, *, status: str | None = None, limit: int = 20) -> Sequence[LearningSession]:
        stmt = select(LearningSession).order_by(LearningSession.id.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(LearningSession.status == status)
        return list(self._s.scalars(stmt))

    def add_session(self, session: LearningSession, steps: Sequence[LearningSessionStep]) -> None:
        self._s.add(session)
        self._s.flush()
        for step in steps:
            step.session_id = session.id
            self._s.add(step)
        self._s.flush()
