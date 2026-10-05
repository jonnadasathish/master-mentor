"""Index review (Slice 12): the hot read paths of the engines and pages are index-backed (EXPLAIN)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker

from app.domain.clock import FixedClock
from app.models.system import MentorRunTrigger
from app.services.mentor_service import MentorService
from tests.db.test_replay_audit import synthetic_history

pytestmark = pytest.mark.db

HOT_QUERIES = {
    "evidence by skill": (
        "SELECT * FROM evidence WHERE ruleset_version = 'v1' AND skill_id = 5 ORDER BY observed_on",
        "evidence",
    ),
    "attempts by local date": (
        "SELECT * FROM problem_attempts WHERE attempted_on BETWEEN :a AND :b",
        "problem_attempts",
    ),
    "attempts by problem": ("SELECT * FROM problem_attempts WHERE problem_id = 27", "problem_attempts"),
    "assessments by battery item": (
        "SELECT * FROM assessments WHERE battery_item_key = 'M0-B04'",
        "assessments",
    ),
    "revision queue": (
        "SELECT * FROM revision_items WHERE state = 'ACTIVE' AND due_date <= :b",
        "revision_items",
    ),
    "plan of a date": ("SELECT * FROM daily_plans WHERE plan_date = :a", "daily_plans"),
    "latest run": ("SELECT * FROM mentor_runs WHERE as_of_date = :b ORDER BY id DESC", "mentor_runs"),
    "readiness history": (
        "SELECT * FROM readiness_snapshots WHERE snapshot_date BETWEEN :a AND :b",
        "readiness_snapshots",
    ),
    "audit of an entity": (
        "SELECT * FROM audit_log WHERE entity_type = 'goal' AND entity_id = '1'",
        "audit_log",
    ),
}


def test_hot_queries_use_indexes(catalog_engine: Engine) -> None:
    factory = sessionmaker(bind=catalog_engine, expire_on_commit=False)
    with factory() as session:
        days = synthetic_history(session, 14)
        MentorService(session, FixedClock(datetime(2026, 7, 19, 12, tzinfo=UTC))).recalculate(
            MentorRunTrigger.REBUILD, as_of=days[-1]
        )
    params = {"a": date(2026, 7, 6), "b": date(2026, 7, 19)}
    missing = []
    with catalog_engine.connect() as c:
        c.execute(text("ANALYZE TABLE evidence, problem_attempts, assessments, revision_items, mentor_runs"))
        for name, (sql, table) in HOT_QUERIES.items():
            plan = c.execute(text("EXPLAIN " + sql), params).mappings().all()
            row = next((r for r in plan if r["table"] == table), None)
            if row is None:
                # Resolved at plan time through a unique/primary key ("no matching row in const table").
                extra = " ".join(str(r["Extra"]) for r in plan)
                if "const table" not in extra and "Impossible WHERE" not in extra:
                    missing.append(f"{name}: {[dict(r) for r in plan]}")
            elif row["possible_keys"] is None and row["key"] is None:
                missing.append(f"{name}: {dict(row)}")
    assert missing == []
