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
PROFILE_TABLES = {"starting_profile"}
LEARNING_TABLES = {
    "learning_tracks",
    "learning_topics",
    "learning_topic_skills",
    "learning_content",
    "learning_content_skills",
    "learning_sessions",
    "learning_session_steps",
}
SPEAKING_TABLES = {"speaking_practices"}
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
    | PROFILE_TABLES
    | LEARNING_TABLES
    | SPEAKING_TABLES
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
    assert set(inspect(migrated).get_table_names()) == (ALL_TABLES - SPEAKING_TABLES) | {"alembic_version"}
    command.upgrade(alembic_config(test_db_url), "head")
    assert set(inspect(migrated).get_table_names()) == ALL_TABLES | {"alembic_version"}


def test_downgrade_two_removes_speaking_and_learning_only(migrated: Engine, test_db_url: str) -> None:
    command.downgrade(alembic_config(test_db_url), "-2")
    assert set(inspect(migrated).get_table_names()) == (ALL_TABLES - LEARNING_TABLES - SPEAKING_TABLES) | {
        "alembic_version"
    }


def test_downgrade_to_base_removes_everything(migrated: Engine, test_db_url: str) -> None:
    command.downgrade(alembic_config(test_db_url), "base")
    assert set(inspect(migrated).get_table_names()) == {"alembic_version"}


# ------------------------------------------------------------------------------ speaking_practices (0013)
ASSESSMENT_SQL = (
    "INSERT INTO assessments (kind, observed_on, observed_at, mode, source_key, notes_used, "
    "reference_used, hints_used, timed, peer_evaluated, applied, unseen_variant, difficulty, created_at) "
    "VALUES ('CONCEPT_EXPLAIN', '2026-10-07', UTC_TIMESTAMP(6), 'PRACTICE', 'content:comm.test', "
    "0, 0, 0, 0, 0, 0, 0, 'EASY', UTC_TIMESTAMP(6))"
)


def _insert_practice(connection: object, assessment_id: int, source: str, transcript: str | None) -> None:
    connection.execute(  # type: ignore[attr-defined]
        text(
            "INSERT INTO speaking_practices (assessment_id, source, transcript, duration_seconds, "
            "word_count, filler_count, metrics_json, metrics_version, created_at) VALUES "
            "(:a, :s, :t, 42, 80, 2, :m, 'speak-v1', UTC_TIMESTAMP(6))"
        ),
        {"a": assessment_id, "s": source, "t": transcript, "m": '{"filler_per_100_words": 2}'},
    )


def _new_assessment(connection: object) -> int:
    result = connection.execute(text(ASSESSMENT_SQL))  # type: ignore[attr-defined]
    return int(result.lastrowid)


def test_speaking_practices_columns_have_no_audio_field(migrated: Engine) -> None:
    columns = {c["name"] for c in inspect(migrated).get_columns("speaking_practices")}
    assert columns == {
        "id",
        "assessment_id",
        "source",
        "transcript",
        "duration_seconds",
        "word_count",
        "filler_count",
        "metrics_json",
        "metrics_version",
        "self_reflection",
        "created_at",
    }


def test_speaking_practice_insert_read_and_one_per_assessment(migrated: Engine) -> None:
    with migrated.begin() as connection:
        a = _new_assessment(connection)
        _insert_practice(connection, a, "BROWSER", "First, the root cause was an index.")
        row = connection.execute(text("SELECT source, transcript, word_count FROM speaking_practices")).one()
        assert (row.source, row.word_count) == ("BROWSER", 80) and "root cause" in row.transcript
    with pytest.raises(DBAPIError), migrated.begin() as connection:
        _insert_practice(connection, a, "MANUAL", None)  # a second practice for the same observation
    with migrated.begin() as connection:
        connection.execute(text("DELETE FROM speaking_practices"))
        connection.execute(text("DELETE FROM assessments"))


@pytest.mark.parametrize(
    ("source", "transcript"),
    [("BROWSER", None), ("MANUAL", "text that a manual review cannot have"), ("AUDIO", "x")],
)
def test_speaking_practice_constraints_reject_bad_rows(
    migrated: Engine, source: str, transcript: str | None
) -> None:
    with migrated.begin() as connection:
        a = _new_assessment(connection)
    with pytest.raises(DBAPIError), migrated.begin() as connection:
        connection.execute(text("SET SESSION sql_mode = 'STRICT_ALL_TABLES'"))
        _insert_practice(connection, a, source, transcript)
    with migrated.begin() as connection:
        connection.execute(text("DELETE FROM assessments"))


def test_speaking_practice_requires_an_existing_assessment(migrated: Engine) -> None:
    with pytest.raises(DBAPIError), migrated.begin() as connection:
        _insert_practice(connection, 999999, "MANUAL", None)


def test_0013_is_additive_and_leaves_existing_rows_alone(test_engine: Engine, test_db_url: str) -> None:
    drop_everything(test_engine)
    config = alembic_config(test_db_url)
    command.upgrade(config, "0012_learning")
    with test_engine.begin() as connection:
        assessment_id = _new_assessment(connection)
        before = connection.execute(text("SELECT * FROM assessments")).all()
    command.upgrade(config, "head")
    with test_engine.begin() as connection:
        after = connection.execute(text("SELECT * FROM assessments")).all()
        assert after == before  # existing evidence is byte-for-byte unchanged
        assert connection.execute(text("SELECT COUNT(*) FROM speaking_practices")).scalar_one() == 0
        _insert_practice(connection, assessment_id, "MANUAL", None)
    with pytest.raises(DBAPIError), test_engine.begin() as connection:
        connection.execute(text("DELETE FROM assessments"))  # still referenced: history cannot vanish
    command.downgrade(config, "0012_learning")
    with test_engine.begin() as connection:
        assert connection.execute(text("SELECT * FROM assessments")).all() == before
    drop_everything(test_engine)
    command.upgrade(config, "head")
