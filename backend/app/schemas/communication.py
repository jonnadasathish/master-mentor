"""Communication API payloads (D-087). Read models only; the evidence wording is built on the server."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.learning import SpeakingResultOut


class CommunicationSkillOut(BaseModel):
    key: str
    name: str
    score: int | None
    level: int | None
    confidence: str
    measured: int
    manual: int
    other: int
    self_reported: bool


class CommunicationAreaOut(BaseModel):
    key: str
    title: str
    status: str  # NOT_STARTED | DEVELOPING | WORKING | STRONG
    status_label: str
    summary: str
    skills_total: int
    skills_with_evidence: int
    measured_rows: int
    manual_rows: int
    other_rows: int
    self_reported_only: int
    self_report: str | None  # what the learner said about this area; context only, never evidence
    skills: list[CommunicationSkillOut]


class CommunicationReadinessOut(BaseModel):
    """Read-only (V1 boundary): not a readiness component, never part of Overall Readiness."""

    areas: list[CommunicationAreaOut]
    note: str


class SpeechPreviewIn(BaseModel):
    """A transcript to measure before submitting. Nothing is stored."""

    model_config = ConfigDict(extra="forbid")

    content_key: str = Field(min_length=1, max_length=80)
    transcript: str = Field(min_length=1, max_length=8000)
    duration_seconds: int = Field(ge=1, le=3600)


class SpeechPreviewOut(BaseModel):
    content_key: str
    speaking: SpeakingResultOut


class SpeakingHistoryRowOut(BaseModel):
    """One recorded speaking practice. Counts only: the transcript is never part of the history list."""

    assessment_id: int
    skill: str
    skill_name: str
    content_key: str | None
    observed_on: date
    source: str  # BROWSER (measured transcript) | MANUAL (self-review)
    duration_seconds: int
    word_count: int
    filler_count: int
    filler_per_100_words: int | None
    timed: bool
    reference_used: bool
    reflection: str | None


class SpeakingHistoryOut(BaseModel):
    rows: list[SpeakingHistoryRowOut]
    note: str
