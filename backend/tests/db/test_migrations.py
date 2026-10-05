"""Database initialization: the baseline migration applies to an empty DB, matches the models, and
reverses cleanly. Runs against the isolated *_test database only."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from app.models import Base

pytestmark = pytest.mark.db

BACKEND_DIR = Path(__file__).resolve().parents[2]
BASELINE_TABLES = {"app_settings", "audit_log", "mentor_runs"}
CATALOG_TABLES = {
    "skill_groups",
    "skills",
    "skill_prerequisites",
    "role_profiles",
    "role_skill_targets",
    "problems",
    "problem_skills",
    "mission_templates",
    "roadmap_milestones",
    "roadmap_milestone_skills",
    "baseline_items",
    "catalog_loads",
}
ACTIVITY_TABLES = {"problem_attempts", "attempt_mistakes"}
EVIDENCE_TABLES = {"assessments", "assessment_skills", "evidence", "skill_states", "skill_daily_snapshots"}
GAP_TABLES = {"goals", "gap_states"}
REVISION_TABLES = {"revision_items", "revision_item_actions"}
PLAN_TABLES = {"daily_plans", "plan_items"}
READINESS_TABLES = {"readiness_snapshots"}
MOCK_CONTENT_TABLES = {
    "mocks",
    "mock_rounds",
    "mock_round_skills",
    "behavioral_stories",
    "story_competencies",
    "projects",
    "assessment_prompts",
}
REVIEW_TABLES = {"weekly_reviews"}
ALL_TABLES = (
    BASELINE_TABLES
    | CATALOG_TABLES
    | ACTIVITY_TABLES
    | EVIDENCE_TABLES
    | GAP_TABLES
    | REVISION_TABLES
    | PLAN_TABLES
    | READINESS_TABLES
    | MOCK_CONTENT_TABLES
    | REVIEW_TABLES
)


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["db_url"] = url
    return config


def drop_everything(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspect(connection).get_table_names():
            connection.execute(text(f"DROP TABLE `{table}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture
def migrated(test_engine: Engine, test_db_url: str) -> Iterator[Engine]:
    drop_everything(test_engine)  # start from a truly empty database
    command.upgrade(alembic_config(test_db_url), "head")
    yield test_engine
    drop_everything(test_engine)
    command.upgrade(alembic_config(test_db_url), "head")  # leave a migrated, empty DB for other tests


def test_upgrade_from_empty_creates_all_tables(migrated: Engine) -> None:
    tables = set(inspect(migrated).get_table_names())
    assert tables == ALL_TABLES | {"alembic_version"}


def test_schema_matches_models_exactly(migrated: Engine) -> None:
    with migrated.connect() as connection:
        diff = compare_metadata(
            MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata
        )
    assert diff == [], f"models and migrations differ: {diff}"


def test_tables_use_utf8mb4_innodb(migrated: Engine) -> None:
    with migrated.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_name, engine, table_collation FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name IN ('app_settings','audit_log','mentor_runs')"
            )
        ).all()
    assert {(r[0], r[1], r[2]) for r in rows} == {
        (name, "InnoDB", "utf8mb4_0900_ai_ci") for name in BASELINE_TABLES
    }
    with migrated.connect() as connection:
        catalog_rows = connection.execute(
            text(
                "SELECT engine, table_collation FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name <> 'alembic_version'"
            )
        ).all()
    assert {(r[0], r[1]) for r in catalog_rows} == {("InnoDB", "utf8mb4_0900_ai_ci")}


def test_app_settings_bootstrap_row_and_single_row_rule(migrated: Engine) -> None:
    with migrated.connect() as connection:
        row = connection.execute(text("SELECT id, timezone, display_name FROM app_settings")).one()
        assert row.id == 1 and row.display_name == "Owner"
        assert row.timezone  # IANA name from APP_DEFAULT_TIMEZONE
    with pytest.raises(DBAPIError), migrated.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app_settings (id, timezone, display_name, created_at) "
                "VALUES (2, 'UTC', 'x', NOW(6))"
            )
        )


def test_mentor_run_trigger_enum_rejects_unknown_values(migrated: Engine) -> None:
    with pytest.raises(DBAPIError), migrated.begin() as connection:
        connection.execute(text("SET SESSION sql_mode = 'STRICT_ALL_TABLES'"))
        connection.execute(
            text(
                "INSERT INTO mentor_runs "
                "(run_at, as_of_date, `trigger`, ruleset_version, seed_version, input_hash) "
                "VALUES (UTC_TIMESTAMP(6), '2026-10-04', 'DAILY', 'v1', 'seed-v1', REPEAT('a', 64))"
            )
        )


def test_connection_session_time_zone_is_utc(migrated: Engine) -> None:
    with migrated.connect() as connection:
        assert connection.execute(text("SELECT @@session.time_zone")).scalar_one() == "+00:00"


def test_downgrade_one_then_upgrade_again(migrated: Engine, test_db_url: str) -> None:
    command.downgrade(alembic_config(test_db_url), "-1")
    assert set(inspect(migrated).get_table_names()) == (ALL_TABLES - REVIEW_TABLES) | {"alembic_version"}
    command.upgrade(alembic_config(test_db_url), "head")
    assert set(inspect(migrated).get_table_names()) == ALL_TABLES | {"alembic_version"}


def test_downgrade_to_base_removes_everything(migrated: Engine, test_db_url: str) -> None:
    command.downgrade(alembic_config(test_db_url), "base")
    assert set(inspect(migrated).get_table_names()) == {"alembic_version"}
