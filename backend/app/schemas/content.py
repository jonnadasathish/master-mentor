"""Content payloads: behavioral stories, projects, assessment prompts (never evidence by themselves)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assessment import AssessmentKind

Key = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_.-]*$")


class StoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=160)
    situation: str = Field(min_length=1, max_length=4000)
    task: str = Field(min_length=1, max_length=4000)
    action: str = Field(min_length=1, max_length=4000)
    result: str = Field(min_length=1, max_length=4000)
    metric: str | None = Field(default=None, max_length=255)
    learning: str | None = Field(default=None, max_length=4000)
    competencies: list[str] = Field(min_length=1, max_length=6)  # position 1 owns the revision item


class StoryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=160)
    situation: str | None = Field(default=None, max_length=4000)
    task: str | None = Field(default=None, max_length=4000)
    action: str | None = Field(default=None, max_length=4000)
    result: str | None = Field(default=None, max_length=4000)
    metric: str | None = Field(default=None, max_length=255)
    learning: str | None = Field(default=None, max_length=4000)
    archived: bool | None = None


class StoryOut(BaseModel):
    id: int
    title: str
    situation: str
    task: str
    action: str
    result: str
    metric: str | None
    learning: str | None
    competencies: list[str]
    archived: bool
    created_at: datetime
    updated_at: datetime


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_key: str = Key
    name: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=1, max_length=4000)
    architecture_notes: str | None = Field(default=None, max_length=8000)


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=160)
    summary: str | None = Field(default=None, max_length=4000)
    architecture_notes: str | None = Field(default=None, max_length=8000)


class ProjectOut(BaseModel):
    id: int
    project_key: str
    name: str
    summary: str
    architecture_notes: str | None
    created_at: datetime
    updated_at: datetime


class PromptInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_key: str = Field(min_length=2, max_length=96, pattern=r"^[a-z0-9][a-z0-9_.:-]*$")
    skill: str = Field(min_length=1, max_length=64)
    kind: AssessmentKind
    prompt_text: str = Field(min_length=1, max_length=4000)
    answer_key_text: str | None = Field(default=None, max_length=8000)


class PromptOut(BaseModel):
    id: int
    prompt_key: str
    skill: str
    kind: str
    prompt_text: str
    answer_key_text: str | None
    source_key: str  # use as the assessment source_key: prompt:<prompt_key>
