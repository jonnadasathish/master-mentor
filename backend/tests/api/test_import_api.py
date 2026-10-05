"""Slice 12: export -> wipe -> import reproduces every derived value; preview validates; commit is guarded."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db
CONFIRM = "IMPORT-INTO-EMPTY-DATABASE"


def populate(client: TestClient) -> None:
    post(client, "/goals", {"target_date": "2027-06-28"})
    post(client, "/problem-attempts", {**SOLVED, "attempted_at": "2026-10-01T06:00:00Z"})
    post(
        client,
        "/problem-attempts",
        {
            **SOLVED,
            "problem_id": 27,
            "outcome": "FAIL",
            "mistakes": ["WRONG_PATTERN"],
            "attempted_at": "2026-10-02T06:00:00Z",
        },
    )
    post(
        client,
        "/assessments",
        {
            "kind": "CONCEPT_EXPLAIN",
            "source_key": "prompt:idx",
            "observed_at": "2026-10-03T06:00:00Z",
            "skills": [{"skill": "db.indexing", "outcome_points": 85}],
        },
    )
    post(
        client,
        "/mocks",
        {
            "source": "PEER",
            "occurred_at": "2026-10-03T09:00:00Z",
            "rounds": [
                {
                    "round_type": "SYSTEM_DESIGN",
                    "duration_minutes": 45,
                    "round_score": 60,
                    "skills": [{"skill": "sd.caching", "outcome_points": 55, "is_weakness": True}],
                }
            ],
        },
    )
    post(
        client,
        "/stories",
        {
            "title": "Story",
            "situation": "s",
            "task": "t",
            "action": "a",
            "result": "r",
            "competencies": ["behavioral.ownership"],
        },
    )
    get(client, "/today")


def derived(engine: Engine) -> dict[str, list[tuple[Any, ...]]]:
    queries = {
        "states": "SELECT s.skill_key, st.score, st.level, st.confidence, st.effective_score "
        "FROM skill_states st JOIN skills s ON s.id = st.skill_id ORDER BY s.skill_key",
        "gaps": "SELECT s.skill_key, g.priority, g.status "
        "FROM gap_states g JOIN skills s ON s.id = g.skill_id ORDER BY s.skill_key",
        "revision": "SELECT item_key, state, due_date, interval_index FROM revision_items ORDER BY item_key",
        "readiness": "SELECT snapshot_date, state, weighted_score "
        "FROM readiness_snapshots ORDER BY snapshot_date",
    }
    with engine.connect() as c:
        return {k: [tuple(r) for r in c.execute(text(q)).all()] for k, q in queries.items()}


def wipe(engine: Engine) -> None:
    tables = [
        "plan_items",
        "daily_plans",
        "weekly_reviews",
        "story_competencies",
        "behavioral_stories",
        "mock_round_skills",
        "mock_rounds",
        "mocks",
        "assessment_skills",
        "assessments",
        "attempt_mistakes",
        "problem_attempts",
        "revision_item_actions",
        "projects",
        "assessment_prompts",
        "evidence",
        "skill_states",
        "skill_daily_snapshots",
        "gap_states",
        "revision_items",
        "readiness_snapshots",
        "mentor_runs",
        "goals",
    ]
    with engine.begin() as c:
        c.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for t in tables:
            c.execute(text(f"DELETE FROM `{t}`"))
        c.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def test_round_trip_reproduces_all_derived_state(activity_client: TestClient, catalog_engine: Engine) -> None:
    populate(activity_client)
    post(activity_client, "/admin/rebuild", {}, status=200)
    before = derived(catalog_engine)
    doc = json.loads(activity_client.get("/api/v1/export/json").content)
    assert doc["format_version"] == 2 and doc["id_maps"]["skills"]

    blocked = post(activity_client, "/import/preview", doc, status=200)["data"]
    assert blocked["ok"] is False and "already has preparation data" in blocked["errors"][0]

    wipe(catalog_engine)
    preview = post(activity_client, "/import/preview", doc, status=200)["data"]
    assert preview["ok"] is True, preview["errors"]
    assert preview["counts"]["problem_attempts"] == 2 and preview["counts"]["mocks"] == 1

    post(activity_client, "/import/commit", {"document": doc, "confirm": "yes"}, status=422)
    result = post(activity_client, "/import/commit", {"document": doc, "confirm": CONFIRM}, status=200)[
        "data"
    ]
    assert result["inserted"]["problem_attempts"] == 2 and result["rebuild"]["runs"] >= 1
    assert derived(catalog_engine) == before
    attempts = get(activity_client, "/problem-attempts")["data"]
    assert sorted(a["attempted_on"] for a in attempts) == ["2026-10-01", "2026-10-02"]
    with catalog_engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM audit_log WHERE action = 'IMPORT'")).scalar_one() == 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(format_version=1), "format_version"),
        (lambda d: d.update(seed_version="seed-v0"), "differs from the loaded catalog"),
        (lambda d: d["tables"].update(secrets=[]), "unknown table"),
        (lambda d: d["tables"]["problem_attempts"][0].update(score=99), "unknown columns"),
        (lambda d: d["id_maps"]["skills"].clear(), "has no matching skill"),
    ],
)
def test_preview_rejects_invalid_documents(
    activity_client: TestClient, catalog_engine: Engine, mutate: Any, message: str
) -> None:
    populate(activity_client)
    doc = json.loads(activity_client.get("/api/v1/export/json").content)
    wipe(catalog_engine)
    broken = copy.deepcopy(doc)
    mutate(broken)
    preview = post(activity_client, "/import/preview", broken, status=200)["data"]
    assert preview["ok"] is False and any(message in e for e in preview["errors"]), preview["errors"]
    error = post(activity_client, "/import/commit", {"document": broken, "confirm": CONFIRM}, status=422)[
        "error"
    ]
    assert error["code"] == "VALIDATION_ERROR"
    with catalog_engine.connect() as c:  # nothing was written
        assert c.execute(text("SELECT COUNT(*) FROM problem_attempts")).scalar_one() == 0
