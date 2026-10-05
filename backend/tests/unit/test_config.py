from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Environment, Settings

DB_URL = "mysql+pymysql://user:s3cret-value@db:3306/mastermentor"


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not depend on the container's real environment variables."""
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


def make(**overrides: object) -> Settings:
    values: dict[str, object] = {"database_url": DB_URL} | overrides
    return Settings(**values)  # type: ignore[arg-type]


def test_defaults_are_local_and_deterministic() -> None:
    settings = make()
    assert settings.app_env is Environment.DEVELOPMENT
    assert settings.app_host == "127.0.0.1"
    assert settings.ruleset_version == "v1"
    assert settings.app_default_timezone == "Asia/Kolkata"
    assert settings.db_pool_pre_ping is True


def test_database_url_is_required() -> None:
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_secrets_never_appear_in_repr_or_dump() -> None:
    settings = make()
    assert "s3cret-value" not in repr(settings)
    assert "s3cret-value" not in str(settings.model_dump())
    assert settings.database_url.get_secret_value() == DB_URL


def test_unknown_timezone_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown IANA timezone"):
        make(app_default_timezone="Mars/Olympus")


def test_unregistered_ruleset_rejected() -> None:
    with pytest.raises(ValidationError, match="not registered"):
        make(ruleset_version="v999")


def test_only_pymysql_urls_accepted() -> None:
    with pytest.raises(ValidationError, match="mysql\\+pymysql"):
        make(database_url="sqlite:///tmp.db")


def test_environment_variables_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DB_POOL_SIZE", "3")
    settings = Settings()  # type: ignore[call-arg]
    assert settings.app_env is Environment.TEST
    assert settings.db_pool_size == 3


def test_settings_are_immutable() -> None:
    settings = make()
    with pytest.raises(ValidationError):
        settings.ruleset_version = "v2"
