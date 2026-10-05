"""Revision read models and actions."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class RevisionItemOut(BaseModel):
    item_key: str
    item_type: str
    skill: str
    skill_name: str
    tier: str | None
    importance: int | None
    parked: bool
    state: str
    suspend_reason: str | None
    interval_index: int
    due_date: date | None
    days_overdue: int
    lapses: int
    needs_reinforcement: bool
    minutes: int  # including the reinforcement refresh
    bucket: str  # overdue | due | upcoming | maintenance | suspended | graduated
    review_kind: str  # observation to record: ATTEMPT or an assessment kind
    subject_ref: str
    last_reviewed_on: date | None


class RevisionListOut(BaseModel):
    backlog_minutes: int
    cap_minutes: int
    triage_threshold_minutes: int
    counts: dict[str, int]
    items: list[RevisionItemOut]
