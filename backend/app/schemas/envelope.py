"""Standard response envelopes (API_SPEC.md §1).

Success:  {"data": <payload>, "meta": {as_of_date?, ruleset_version?, seed_version?, run_id?, count?}}
Write:    success + "effects": {run_id, skill_deltas[...]} (observation writes, D-056)
Error:    {"error": {"code": <ErrorCode>, "message": str, "details": {}}}

Unset meta fields are omitted; the success and error shapes never vary per endpoint.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: date | None = None
    ruleset_version: str | None = None
    seed_version: str | None = None
    run_id: int | None = None
    count: int | None = None


class Envelope[T](BaseModel):
    data: T
    meta: Meta = Field(default_factory=Meta)


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"  # 422
    NOT_FOUND = "NOT_FOUND"  # 404
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"  # 405 (added in Slice 1, D-040)
    CONFLICT = "CONFLICT"  # 409
    INVALID_STATE = "INVALID_STATE"  # 409
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"  # 503, e.g. database unreachable (D-040)
    SEED_INVALID = "SEED_INVALID"  # 500
    INTERNAL = "INTERNAL"  # 500


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody


def success(data: BaseModel | dict[str, Any] | list[Any], meta: Meta | None = None) -> dict[str, Any]:
    """Serialize a success envelope. ``None`` meta fields are omitted; ``data`` is kept verbatim."""
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    return {"data": payload, "meta": (meta or Meta()).model_dump(mode="json", exclude_none=True)}


def write_success(
    data: BaseModel | dict[str, Any] | list[Any], meta: Meta, effects: dict[str, Any]
) -> dict[str, Any]:
    """Observation write envelope: the stored record + the effects of the synchronous mentor run (D-056)."""
    return {**success(data, meta), "effects": effects}


def error(code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return ErrorEnvelope(error=ErrorBody(code=code, message=message, details=details or {})).model_dump(
        mode="json"
    )
