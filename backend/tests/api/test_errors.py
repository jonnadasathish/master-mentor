"""Every error path returns the standard error envelope and never leaks internals."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import Query
from fastapi.testclient import TestClient

from app.errors import AppError
from app.main import create_app
from app.schemas.envelope import ErrorCode


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    @app.get("/api/v1/_test/validated")
    def validated(count: int = Query(ge=1)) -> dict[str, int]:
        return {"count": count}

    @app.get("/api/v1/_test/conflict")
    def conflict() -> None:
        raise AppError(ErrorCode.CONFLICT, "Duplicate request.", 409, {"client_request_id": "abc"})

    @app.get("/api/v1/_test/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail: password=hunter2")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def assert_error(body: dict[str, object], code: str) -> dict[str, object]:
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == code
    return error


def test_unknown_route_is_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert_error(response.json(), "NOT_FOUND")


def test_wrong_method(client: TestClient) -> None:
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    assert_error(response.json(), "METHOD_NOT_ALLOWED")


def test_validation_error_lists_fields(client: TestClient) -> None:
    response = client.get("/api/v1/_test/validated", params={"count": 0})
    assert response.status_code == 422
    error = assert_error(response.json(), "VALIDATION_ERROR")
    details = error["details"]
    assert isinstance(details, dict)
    assert details["errors"][0]["loc"] == ["query", "count"]


def test_app_error_maps_code_status_and_details(client: TestClient) -> None:
    response = client.get("/api/v1/_test/conflict")
    assert response.status_code == 409
    error = assert_error(response.json(), "CONFLICT")
    assert error["details"] == {"client_request_id": "abc"}


def test_unhandled_exception_is_internal_without_leaking(client: TestClient) -> None:
    response = client.get("/api/v1/_test/boom")
    assert response.status_code == 500
    assert_error(response.json(), "INTERNAL")
    assert "hunter2" not in response.text and "RuntimeError" not in response.text
