"""Alembic environment. The target URL is DATABASE_URL from app.config, unless the caller passes
``-x db_url=...`` or sets ``config.attributes["db_url"]`` (used by the migration tests)."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings
from app.models import Base

config = context.config
# Configure logging for CLI runs only; programmatic runs (tests) keep their own logging.
if config.config_file_name and not config.attributes.get("db_url"):
    fileConfig(config.config_file_name, disable_existing_loggers=False)
target_metadata = Base.metadata


def _database_url() -> str:
    if url := config.attributes.get("db_url"):
        return str(url)
    if url := context.get_x_argument(as_dictionary=True).get("db_url"):
        return url
    return get_settings().database_url.get_secret_value()


def run_migrations_offline() -> None:
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(
        _database_url(),
        poolclass=pool.NullPool,
        connect_args={"init_command": "SET time_zone = '+00:00'"},
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
