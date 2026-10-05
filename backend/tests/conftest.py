from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.infrastructure.db import get_session
from app.main import create_app


@pytest.fixture
def app_client() -> Iterator[TestClient]:
    """Client for tests that must not touch any database (DB session dependency is not overridden)."""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """URL of the isolated test database. Refuses anything not named *_test (protects real data)."""
    url = get_settings().test_database_url
    if url is None:
        pytest.fail("TEST_DATABASE_URL is not set; DB tests must run inside the compose backend service")
    value = url.get_secret_value()
    database = make_url(value).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"refusing to run DB tests against non-test database {database!r}")
    return value


@pytest.fixture(scope="session")
def test_engine(test_db_url: str) -> Iterator[Engine]:
    engine = create_engine(test_db_url, connect_args={"init_command": "SET time_zone = '+00:00'"})
    yield engine
    engine.dispose()


@pytest.fixture
def db_client(test_engine: Engine) -> Iterator[TestClient]:
    """Client whose request sessions are bound to the test database."""
    factory = sessionmaker(bind=test_engine)

    def _session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = _session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _alembic_config(url: str) -> object:
    from pathlib import Path

    from alembic.config import Config

    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    config.attributes["db_url"] = url
    return config


@pytest.fixture
def catalog_engine(test_engine: Engine, test_db_url: str) -> Iterator[Engine]:
    """Test DB migrated to head with an EMPTY catalog (and empty audit log)."""
    from alembic import command

    from tests.catalog_helpers import clear_catalog

    command.upgrade(_alembic_config(test_db_url), "head")  # type: ignore[arg-type]
    clear_catalog(test_engine)
    yield test_engine
    clear_catalog(test_engine)


@pytest.fixture
def catalog_session(catalog_engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=catalog_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_client(catalog_engine: Engine) -> Iterator[TestClient]:
    """API client over a test DB loaded with the real seed."""
    from datetime import UTC, datetime

    from app.domain.clock import FixedClock
    from app.services.seed_service import SeedLoader
    from tests.catalog_helpers import SEED_DIR

    factory = sessionmaker(bind=catalog_engine)
    with factory() as session:
        SeedLoader(session, FixedClock(datetime(2026, 10, 4, 12, 0, tzinfo=UTC))).load(SEED_DIR)

    def _session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = _session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def db_client_empty_catalog(catalog_engine: Engine) -> Iterator[TestClient]:
    factory = sessionmaker(bind=catalog_engine)

    def _session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = _session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


FIXED_NOW = "2026-10-04T12:00:00+00:00"


@pytest.fixture
def activity_client(catalog_engine: Engine) -> Iterator[TestClient]:
    """Seeded test DB + a frozen clock (2026-10-04 12:00 UTC) for activity capture tests."""
    from datetime import datetime

    from app.api.deps import get_clock
    from app.domain.clock import FixedClock
    from app.services.seed_service import SeedLoader
    from tests.catalog_helpers import SEED_DIR

    clock = FixedClock(datetime.fromisoformat(FIXED_NOW))
    factory = sessionmaker(bind=catalog_engine)
    with factory() as session:
        SeedLoader(session, clock).load(SEED_DIR)

    def _session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
