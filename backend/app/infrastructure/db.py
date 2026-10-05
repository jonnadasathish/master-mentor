"""Database engine and session management (SQLAlchemy 2, PyMySQL).

Every connection uses UTC (``time_zone = '+00:00'``) so stored DATETIMEs are UTC instants.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def build_engine(url: str, settings: Settings) -> Engine:
    return create_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=settings.db_pool_pre_ping,
        connect_args={"init_command": "SET time_zone = '+00:00'", "connect_timeout": 5},
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return build_engine(settings.database_url.get_secret_value(), settings)


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()
