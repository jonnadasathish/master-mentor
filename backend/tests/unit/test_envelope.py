from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.schemas.envelope import ErrorCode, Meta, error, success


class Payload(BaseModel):
    value: int
    note: str | None


def test_success_envelope_has_exactly_data_and_meta() -> None:
    body = success(Payload(value=1, note=None), Meta(ruleset_version="v1"))
    assert set(body) == {"data", "meta"}
    assert body["data"] == {"value": 1, "note": None}  # data keeps explicit nulls
    assert body["meta"] == {"ruleset_version": "v1"}  # unset meta fields are omitted


def test_meta_serializes_dates_as_iso() -> None:
    body = success({"x": 1}, Meta(as_of_date=date(2026, 10, 4), run_id=7))
    assert body["meta"] == {"as_of_date": "2026-10-04", "run_id": 7}


def test_success_without_meta_has_empty_meta() -> None:
    assert success([1, 2]) == {"data": [1, 2], "meta": {}}


def test_error_envelope_shape() -> None:
    body = error(ErrorCode.NOT_FOUND, "Missing.", {"id": 3})
    assert body == {"error": {"code": "NOT_FOUND", "message": "Missing.", "details": {"id": 3}}}


def test_error_details_default_to_empty_object() -> None:
    assert error(ErrorCode.INTERNAL, "x")["error"]["details"] == {}


def test_error_codes_match_api_spec() -> None:
    assert {c.value for c in ErrorCode} == {
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "METHOD_NOT_ALLOWED",
        "CONFLICT",
        "INVALID_STATE",
        "DEPENDENCY_UNAVAILABLE",
        "SEED_INVALID",
        "INTERNAL",
    }
