"""Stories, projects and assessment prompts. Edits are audited; content is never evidence by itself."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.activity.vocabulary import ASSESSMENT_COMPONENTS
from app.domain.clock import Clock
from app.errors import AppError
from app.models import AssessmentPrompt, AuditLog, BehavioralStory, Project, Skill, StoryCompetency
from app.schemas.content import (
    ProjectInput,
    ProjectOut,
    ProjectPatch,
    PromptInput,
    PromptOut,
    StoryInput,
    StoryOut,
    StoryPatch,
)
from app.schemas.envelope import ErrorCode
from app.services.activity_service import _naive_utc, _validation

STORY_COMPONENTS = ("behavioral",)


class ContentService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock

    def _now(self) -> datetime:
        return _naive_utc(self._clock.now_utc())

    def _audit(self, entity: str, entity_id: str, action: str, payload: dict[str, Any]) -> None:
        self._s.add(
            AuditLog(
                at=self._now(), entity_type=entity, entity_id=entity_id, action=action, payload_json=payload
            )
        )

    def _commit(self) -> None:
        try:
            self._s.commit()
        except IntegrityError as exc:
            self._s.rollback()
            raise AppError(ErrorCode.CONFLICT, "The record conflicts with existing data.", 409) from exc

    # ------------------------------------------------------------------ stories
    def _story_out(self, story: BehavioralStory) -> StoryOut:
        comps = [
            key
            for _, key in self._s.execute(
                select(StoryCompetency, Skill.skill_key)
                .join(Skill, Skill.id == StoryCompetency.skill_id)
                .where(StoryCompetency.story_id == story.id)
                .order_by(StoryCompetency.position)
            ).all()
        ]
        return StoryOut(
            id=story.id,
            title=story.title,
            situation=story.situation,
            task=story.task,
            action=story.action,
            result=story.result,
            metric=story.metric,
            learning=story.learning,
            tradeoffs=story.tradeoffs,
            competencies=comps,
            archived=story.archived_at is not None,
            created_at=story.created_at.replace(tzinfo=UTC),
            updated_at=story.updated_at.replace(tzinfo=UTC),
        )

    def stories(self) -> list[StoryOut]:
        return [
            self._story_out(s) for s in self._s.scalars(select(BehavioralStory).order_by(BehavioralStory.id))
        ]

    def create_story(self, payload: StoryInput) -> StoryOut:
        skills = {
            s.skill_key: s
            for s in self._s.scalars(select(Skill).where(Skill.skill_key.in_(payload.competencies)))
        }
        errors = []
        if len(set(payload.competencies)) != len(payload.competencies):
            errors.append(("competencies", "each skill may appear only once"))
        for key in payload.competencies:
            skill = skills.get(key)
            if skill is None:
                errors.append(("competencies", f"unknown skill {key!r}"))
            elif skill.component not in STORY_COMPONENTS:
                errors.append(("competencies", f"{key!r} is not a behavioral/communication skill"))
        if errors:
            raise _validation(errors)
        now = self._now()
        story = BehavioralStory(
            title=payload.title,
            situation=payload.situation,
            task=payload.task,
            action=payload.action,
            result=payload.result,
            metric=payload.metric,
            learning=payload.learning,
            tradeoffs=payload.tradeoffs,
            created_at=now,
            updated_at=now,
        )
        self._s.add(story)
        self._s.flush()
        for position, key in enumerate(payload.competencies, start=1):
            self._s.add(StoryCompetency(story_id=story.id, skill_id=skills[key].id, position=position))
        self._audit("story", str(story.id), "CREATE_STORY", payload.model_dump(mode="json"))
        self._commit()
        return self._story_out(story)

    def patch_story(self, story_id: int, patch: StoryPatch) -> StoryOut:
        story = self._s.get(BehavioralStory, story_id)
        if story is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Story {story_id} not found.", 404)
        before = self._story_out(story).model_dump(mode="json")
        for field, value in patch.model_dump(exclude_unset=True, exclude={"archived"}).items():
            setattr(story, field, value)
        if patch.archived is not None:
            story.archived_at = self._now() if patch.archived else None
        story.updated_at = self._now()
        self._audit(
            "story",
            str(story_id),
            "UPDATE_STORY",
            {"before": before, "patch": patch.model_dump(mode="json", exclude_unset=True)},
        )
        self._commit()
        return self._story_out(story)

    # ------------------------------------------------------------------ projects
    @staticmethod
    def _project_out(p: Project) -> ProjectOut:
        return ProjectOut(
            id=p.id,
            project_key=p.project_key,
            name=p.name,
            summary=p.summary,
            architecture_notes=p.architecture_notes,
            created_at=p.created_at.replace(tzinfo=UTC),
            updated_at=p.updated_at.replace(tzinfo=UTC),
        )

    def projects(self) -> list[ProjectOut]:
        return [self._project_out(p) for p in self._s.scalars(select(Project).order_by(Project.project_key))]

    def create_project(self, payload: ProjectInput) -> ProjectOut:
        if self._s.scalar(select(Project).where(Project.project_key == payload.project_key)):
            raise AppError(ErrorCode.CONFLICT, f"Project {payload.project_key!r} already exists.", 409)
        now = self._now()
        project = Project(**payload.model_dump(), created_at=now, updated_at=now)
        self._s.add(project)
        self._s.flush()
        self._audit("project", project.project_key, "CREATE_PROJECT", payload.model_dump(mode="json"))
        self._commit()
        return self._project_out(project)

    def patch_project(self, project_key: str, patch: ProjectPatch) -> ProjectOut:
        project = self._s.scalar(select(Project).where(Project.project_key == project_key))
        if project is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Project {project_key!r} not found.", 404)
        before = self._project_out(project).model_dump(mode="json")
        for field, value in patch.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        project.updated_at = self._now()
        self._audit(
            "project",
            project_key,
            "UPDATE_PROJECT",
            {"before": before, "patch": patch.model_dump(mode="json", exclude_unset=True)},
        )
        self._commit()
        return self._project_out(project)

    # ------------------------------------------------------------------ prompts
    def prompts(self, skill: str | None = None) -> list[PromptOut]:
        stmt = select(AssessmentPrompt, Skill.skill_key).join(Skill, Skill.id == AssessmentPrompt.skill_id)
        if skill is not None:
            stmt = stmt.where(Skill.skill_key == skill)
        return [
            PromptOut(
                id=p.id,
                prompt_key=p.prompt_key,
                skill=key,
                kind=p.kind,
                prompt_text=p.prompt_text,
                answer_key_text=p.answer_key_text,
                source_key=f"prompt:{p.prompt_key}",
            )
            for p, key in self._s.execute(stmt.order_by(AssessmentPrompt.prompt_key)).all()
        ]

    def create_prompt(self, payload: PromptInput) -> PromptOut:
        skill = self._s.scalar(select(Skill).where(Skill.skill_key == payload.skill, Skill.active.is_(True)))
        if skill is None:
            raise _validation([("skill", f"unknown or inactive skill {payload.skill!r}")])
        if skill.component not in ASSESSMENT_COMPONENTS[payload.kind]:
            raise _validation(
                [("kind", f"{payload.kind} cannot observe {skill.component} skill {payload.skill!r}")]
            )
        if self._s.scalar(select(AssessmentPrompt).where(AssessmentPrompt.prompt_key == payload.prompt_key)):
            raise AppError(ErrorCode.CONFLICT, f"Prompt {payload.prompt_key!r} already exists.", 409)
        prompt = AssessmentPrompt(
            prompt_key=payload.prompt_key,
            skill_id=skill.id,
            kind=payload.kind,
            prompt_text=payload.prompt_text,
            answer_key_text=payload.answer_key_text,
            created_at=self._now(),
        )
        self._s.add(prompt)
        self._s.flush()
        self._audit("prompt", payload.prompt_key, "CREATE_PROMPT", payload.model_dump(mode="json"))
        self._commit()
        return self.prompts(payload.skill)[
            [p.prompt_key for p in self.prompts(payload.skill)].index(payload.prompt_key)
        ]
