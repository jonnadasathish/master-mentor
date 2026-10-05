"""Stories, projects, assessment prompts (content; audited edits). A new story creates its revision item."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.v1.writes import with_effects
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.models.system import MentorRunTrigger
from app.schemas.content import ProjectInput, ProjectPatch, PromptInput, StoryInput, StoryPatch
from app.schemas.envelope import Meta, success
from app.services.content_service import ContentService

router = APIRouter(tags=["content"])
DbSession = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def _list(items: list[Any]) -> dict[str, Any]:
    return success([i.model_dump(mode="json") for i in items], Meta(count=len(items)))


@router.get("/stories")
def stories(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    return _list(ContentService(session, clock).stories())


@router.post("/stories", status_code=201)
def create_story(session: DbSession, clock: ClockDep, payload: StoryInput) -> dict[str, Any]:
    return with_effects(
        session, clock, ContentService(session, clock).create_story(payload), MentorRunTrigger.OBSERVATION
    )


@router.patch("/stories/{story_id}")
def patch_story(session: DbSession, clock: ClockDep, story_id: int, payload: StoryPatch) -> dict[str, Any]:
    return with_effects(
        session,
        clock,
        ContentService(session, clock).patch_story(story_id, payload),
        MentorRunTrigger.OBSERVATION,
    )


@router.get("/projects")
def projects(session: DbSession, clock: ClockDep) -> dict[str, Any]:
    return _list(ContentService(session, clock).projects())


@router.post("/projects", status_code=201)
def create_project(session: DbSession, clock: ClockDep, payload: ProjectInput) -> dict[str, Any]:
    return success(ContentService(session, clock).create_project(payload))


@router.patch("/projects/{project_key}")
def patch_project(
    session: DbSession, clock: ClockDep, project_key: str, payload: ProjectPatch
) -> dict[str, Any]:
    return success(ContentService(session, clock).patch_project(project_key, payload))


@router.get("/prompts")
def prompts(session: DbSession, clock: ClockDep, skill: str | None = None) -> dict[str, Any]:
    return _list(ContentService(session, clock).prompts(skill))


@router.post("/prompts", status_code=201)
def create_prompt(session: DbSession, clock: ClockDep, payload: PromptInput) -> dict[str, Any]:
    return success(ContentService(session, clock).create_prompt(payload))
