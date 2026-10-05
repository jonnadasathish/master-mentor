from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db import get_session
from app.main import create_app


@pytest.mark.db
def test_health_ok_with_reachable_database(db_client: TestClient) -> None:
    response = db_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "data": {"db": "ok", "ruleset_version": "v1", "seed_version": None},
        "meta": {"ruleset_version": "v1"},
    }


def test_health_reports_unreachable_database_as_503() -> None:
    engine = create_engine(
        "mysql+pymysql://nobody:wrong@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    factory = sessionmaker(bind=engine)

    def broken_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = broken_session
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health")
    engine.dispose()

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "DEPENDENCY_UNAVAILABLE",
            "message": "Database is unreachable.",
            "details": {"db": "unreachable"},
        }
    }
    assert "wrong" not in response.text and "nobody" not in response.text
