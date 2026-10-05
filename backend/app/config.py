"""Typed application configuration, loaded from environment variables (.env via Docker Compose).

Secrets (database credentials) are held as SecretStr so they never appear in logs, reprs or responses.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.rulesets import RULESETS


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", frozen=True)

    app_env: Environment = Environment.DEVELOPMENT
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    frontend_url: str = "http://127.0.0.1:5173"
    log_level: str = "INFO"

    # Used only to initialize app_settings.timezone on first migration; afterwards the
    # persisted app_settings row is authoritative (DECISION_LOG D-039).
    app_default_timezone: str = "Asia/Kolkata"

    # Directory holding the canonical seed YAML files (mounted from ./seed in Docker Compose).
    seed_dir: str = "/seed"

    # Read-only mount of ./backups (docker-compose); LATEST is written by scripts/backup-once.sh.
    backup_dir: str = "/backups"
    backup_max_age_hours: int = Field(default=36, ge=1)

    # Active formula ruleset. Must be a registered version in app.domain.rulesets.
    ruleset_version: str = "v1"

    database_url: SecretStr
    test_database_url: SecretStr | None = None
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60)
    db_pool_pre_ping: bool = True

    @field_validator("app_default_timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA timezone: {value!r}") from exc
        return value

    @field_validator("ruleset_version")
    @classmethod
    def _registered_ruleset(cls, value: str) -> str:
        if value not in RULESETS:
            raise ValueError(f"ruleset {value!r} is not registered; known: {sorted(RULESETS)}")
        return value

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _mysql_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().startswith("mysql+pymysql://"):
            raise ValueError("database URLs must use the mysql+pymysql:// driver")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # values come from the environment
