"""Activity capture API: raw problem attempts and personal problems (Slice 3)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.rulesets import RULESETS
from app.models import AuditLog, ProblemAttempt
from app.services.seed_service import SeedLoader, SeedValidationError
from tests.catalog_helpers import SEED_DIR

pytestmark = pytest.mark.db
API = "/api/v1"
SOLVED = {
    "problem_id": 1,
    "outcome": "PASS",
    "time_seconds": 18 * 60,
    "hints_used": 0,
    "self_rating_before": 4,
    "explanation_score": 8,
    "complexity_correct": True,
}


def post(client: TestClient, path: str, body: dict[str, Any], status: int = 201) -> dict[str, Any]:
    response = client.post(f"{API}{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


def get(client: TestClient, path: str, status: int = 200, **params: Any) -> dict[str, Any]:
    response = client.get(f"{API}{path}", params=params)
    assert response.status_code == status, response.text
    return response.json()


def record(client: TestClient, **overrides: Any) -> dict[str, Any]:
    return post(client, "/problem-attempts", {**SOLVED, **overrides})["data"]


# ------------------------------------------------------------------------------------------ creation


def test_solved_attempt_is_stored_exactly_as_entered(activity_client: TestClient) -> None:
    body = post(activity_client, "/problem-attempts", SOLVED)
    assert set(body) == {"data", "meta", "effects"}  # effects = mentor-run consequences (Slice 4, D-056)
    data = body["data"]
    assert data["problem"] == {
        "id": 1,
        "key": "LEETCODE:two-sum",
        "title": "Two Sum",
        "difficulty": "EASY",
        "source": "CATALOG",
    }
    assert (data["outcome"], data["time_seconds"], data["hints_used"]) == ("PASS", 1080, 0)
    assert (data["self_rating_before"], data["explanation_score"], data["complexity_correct"]) == (4, 8, True)
    assert data["attempted_at"] == "2026-10-04T12:00:00Z"  # server clock default
    assert data["mode"] == "PRACTICE" and data["mistakes"] == [] and data["is_current"] is True
    # The stored record itself carries no interpretation; scores live only in `effects`.
    assert not {"score", "level", "skill_deltas", "gap", "priority", "readiness"} & set(data)


def test_partial_and_failed_attempts(activity_client: TestClient) -> None:
    partial = record(
        activity_client, problem_id=4, outcome="PARTIAL", hints_used=1, mistakes=["EDGE_CASE_MISSED"]
    )
    failed = record(
        activity_client,
        problem_id=27,
        outcome="FAIL",
        time_seconds=31 * 60,
        hints_used=2,
        mistakes=["WRONG_PATTERN", "TIME_OVERRUN"],
        pattern_identified=False,
        self_rating_before=2,
    )
    assert partial["outcome"] == "PARTIAL" and partial["mistakes"] == ["EDGE_CASE_MISSED"]
    assert failed["outcome"] == "FAIL"
    assert failed["mistakes"] == ["WRONG_PATTERN", "TIME_OVERRUN"]  # vocabulary order
    assert failed["pattern_identified"] is False


def test_all_optional_raw_fields_round_trip(activity_client: TestClient) -> None:
    data = record(
        activity_client,
        problem_id=6,
        mode="DIAGNOSTIC",
        attempted_at="2026-10-03T20:00:00Z",
        seen_elsewhere=True,
        solution_viewed=True,
        timed=True,
        time_limit_seconds=1800,
        followup_solved=False,
        execution_rubric={"clarification": 7, "think_aloud": 5},
        self_rating_after=3,
        notes="sliding window invariant was unclear",
    )
    assert data["attempted_on"] == "2026-10-04"  # 20:00 UTC = 01:30 next day in Asia/Kolkata
    assert data["execution_rubric"] == {"clarification": 7, "think_aloud": 5}
    assert (data["timed"], data["time_limit_seconds"], data["seen_elsewhere"]) == (True, 1800, True)


def test_duplicate_client_request_id_is_rejected(activity_client: TestClient) -> None:
    first = record(activity_client, client_request_id="req-12345678")
    body = post(activity_client, "/problem-attempts", {**SOLVED, "client_request_id": "req-12345678"}, 409)
    assert body["error"]["code"] == "CONFLICT" and body["error"]["details"] == {"attempt_id": first["id"]}


# ------------------------------------------------------------------------------------------ validation


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"outcome": "SOLVED"}, "outcome"),
        ({"time_seconds": -1}, "time_seconds"),
        ({"hints_used": -1}, "hints_used"),
        ({"self_rating_before": 6}, "self_rating_before"),
        ({"self_rating_after": 0}, "self_rating_after"),
        ({"explanation_score": 11}, "explanation_score"),
        ({"execution_rubric": {"think_aloud": 12}}, "execution_rubric"),
        ({"execution_rubric": {"charisma": 5}}, "execution_rubric"),
        ({"mistakes": ["FORGOTTEN_CONCEPT"]}, "mistakes"),
        ({"mistakes": ["WRONG_PATTERN", "WRONG_PATTERN"]}, "mistakes"),
        ({"confidence": 4}, "confidence"),  # not a Spec v2 field: self_rating_before/after
        ({"attempted_at": "2026-10-04T12:00:00"}, "attempted_at"),  # naive
        ({"attempted_at": "2026-10-05T12:00:00Z"}, "attempted_at"),  # future
        ({"timed": True, "time_seconds": 600}, "time_limit_seconds"),
        ({"mode": "CASUAL"}, "mode"),
    ],
)
def test_invalid_observations_are_rejected(
    activity_client: TestClient, overrides: dict[str, Any], field: str
) -> None:
    body = post(activity_client, "/problem-attempts", {**SOLVED, **overrides}, 422)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(field in e["loc"] for e in body["error"]["details"]["errors"]), body
    assert get(activity_client, "/problem-attempts")["meta"]["count"] == 0  # nothing written


def test_unknown_problem_is_404(activity_client: TestClient) -> None:
    body = post(activity_client, "/problem-attempts", {**SOLVED, "problem_id": 999}, 404)
    assert body["error"]["code"] == "NOT_FOUND"


# ------------------------------------------------------------------------------------------ history


def test_recent_attempts_newest_first_and_problem_history_chronological(activity_client: TestClient) -> None:
    a = record(activity_client, attempted_at="2026-10-01T10:00:00Z")
    b = record(activity_client, problem_id=27, attempted_at="2026-10-03T10:00:00Z")
    c = record(activity_client, attempted_at="2026-10-02T10:00:00Z")
    assert [x["id"] for x in get(activity_client, "/problem-attempts")["data"]] == [b["id"], c["id"], a["id"]]
    history = get(activity_client, "/problems/LEETCODE:two-sum/attempts")["data"]
    assert [x["id"] for x in history] == [a["id"], c["id"]]
    problem = get(activity_client, "/problems/LEETCODE:two-sum")["data"]
    assert problem["attempt_count"] == 2 and problem["last_attempt"]["id"] == c["id"]


def test_skill_linked_history_and_date_range(activity_client: TestClient) -> None:
    primary = record(activity_client, problem_id=27, attempted_at="2026-09-20T10:00:00Z")  # graph primary
    secondary = record(activity_client, problem_id=31, attempted_at="2026-10-02T10:00:00Z")  # graph secondary
    record(activity_client, problem_id=1)  # hashing, unrelated
    rows = get(activity_client, "/problem-attempts", skill="graph.traversal")["data"]
    assert {(r["id"], r["skill_mapping_bp"]) for r in rows} == {
        (primary["id"], 10000),
        (secondary["id"], 5000),
    }
    ranged = get(activity_client, "/problem-attempts", skill="graph.traversal", **{"from": "2026-10-01"})[
        "data"
    ]
    assert [r["id"] for r in ranged] == [secondary["id"]]
    assert get(activity_client, "/problem-attempts", outcome="FAIL")["meta"]["count"] == 0
    assert (
        get(activity_client, "/problem-attempts", skill="ghost.skill", status=404)["error"]["code"]
        == "NOT_FOUND"
    )


def test_attempt_detail_and_404(activity_client: TestClient) -> None:
    created = record(activity_client, notes="exact text")
    assert get(activity_client, f"/problem-attempts/{created['id']}")["data"] == created
    assert get(activity_client, "/problem-attempts/999999", status=404)["error"]["code"] == "NOT_FOUND"


# ------------------------------------------------------------------------------------------ immutability


def test_correction_appends_and_preserves_the_original(activity_client: TestClient) -> None:
    original = record(activity_client, outcome="PASS", hints_used=0)
    corrected = post(
        activity_client,
        f"/problem-attempts/{original['id']}/corrections",
        {**SOLVED, "outcome": "PARTIAL", "hints_used": 2, "attempted_at": original["attempted_at"]},
    )["data"]
    assert corrected["supersedes_id"] == original["id"] and corrected["id"] != original["id"]

    old = get(activity_client, f"/problem-attempts/{original['id']}")["data"]
    assert (old["outcome"], old["hints_used"]) == ("PASS", 0)  # unchanged
    assert old["superseded_by_id"] == corrected["id"] and old["is_current"] is False

    current = get(activity_client, "/problem-attempts")["data"]
    assert [r["id"] for r in current] == [corrected["id"]]  # latest valid interpretation only
    everything = get(activity_client, "/problem-attempts", include_superseded="true")["data"]
    assert {r["id"] for r in everything} == {original["id"], corrected["id"]}

    again = post(activity_client, f"/problem-attempts/{original['id']}/corrections", SOLVED, 409)
    assert again["error"]["details"] == {"latest_attempt_id": corrected["id"]}


def test_every_write_is_audited(activity_client: TestClient, catalog_engine: Engine) -> None:
    attempt = record(activity_client)
    post(activity_client, f"/problem-attempts/{attempt['id']}/corrections", {**SOLVED, "hints_used": 1})
    post(
        activity_client,
        "/problems",
        {
            "platform_key": "my-graph-drill",
            "title": "My graph drill",
            "difficulty": "MEDIUM",
            "skills": [{"skill": "graph.traversal", "mapping_weight_bp": 10000}],
        },
    )
    with Session(catalog_engine) as session:
        actions = session.scalars(select(AuditLog.action).order_by(AuditLog.id)).all()
    assert actions[-3:] == ["CREATE_PROBLEM_ATTEMPT", "CORRECT_PROBLEM_ATTEMPT", "CREATE_PERSONAL_PROBLEM"]


# ------------------------------------------------------------------------------------------ problems


def test_problem_browsing_filters(activity_client: TestClient) -> None:
    assert get(activity_client, "/problems")["meta"]["count"] == 137
    assert get(activity_client, "/problems", difficulty="HARD")["meta"]["count"] == 24
    assert get(activity_client, "/problems", skill="dp.fundamentals")["meta"]["count"] == 9
    assert [p["key"] for p in get(activity_client, "/problems", q="anagram")["data"]] == [
        "LEETCODE:group-anagrams",
        "LEETCODE:valid-anagram",
    ]
    assert get(activity_client, "/problems", source="PERSONAL")["meta"]["count"] == 0
    assert get(activity_client, "/problems/42")["data"]["key"] == "LEETCODE:lru-cache"
    assert get(activity_client, "/problems/LEETCODE:nope", status=404)["error"]["code"] == "NOT_FOUND"
    assert (
        get(activity_client, "/problems", difficulty="BRUTAL", status=422)["error"]["code"]
        == "VALIDATION_ERROR"
    )


def test_personal_problem_is_separate_from_the_catalog(activity_client: TestClient) -> None:
    created = post(
        activity_client,
        "/problems",
        {
            "platform_key": "my-graph-drill",
            "title": "My graph drill",
            "difficulty": "MEDIUM",
            "skills": [
                {"skill": "graph.traversal", "mapping_weight_bp": 10000},
                {"skill": "graph.grid_multisource", "mapping_weight_bp": 5000},
            ],
        },
    )["data"]
    assert created["source"] == "PERSONAL" and created["id"] >= 1_000_000
    assert created["key"] == "OTHER:my-graph-drill" and created["is_canonical"] is False
    assert get(activity_client, "/problems", source="PERSONAL")["meta"]["count"] == 1
    assert record(activity_client, problem_id=created["id"])["problem"]["source"] == "PERSONAL"

    clash = post(
        activity_client,
        "/problems",
        {
            "platform": "LEETCODE",
            "platform_key": "two-sum",
            "title": "Mine",
            "difficulty": "EASY",
            "skills": [{"skill": "hashing.lookup_frequency", "mapping_weight_bp": 10000}],
        },
        409,
    )
    assert clash["error"]["details"]["source"] == "CATALOG"  # cannot overwrite a seeded row
    bad = post(
        activity_client,
        "/problems",
        {
            "platform_key": "x-y",
            "title": "Bad",
            "difficulty": "EASY",
            "skills": [{"skill": "ghost.skill", "mapping_weight_bp": 5000}],
        },
        422,
    )
    messages = " ".join(e["msg"] for e in bad["error"]["details"]["errors"])
    assert "exactly one skill must be primary" in messages and "ghost.skill" in messages


# ------------------------------------------------------------------------------------------ seed integration


def test_reseeding_keeps_attempts_and_identities(activity_client: TestClient, catalog_engine: Engine) -> None:
    attempt = record(activity_client, problem_id=27)
    factory = sessionmaker(bind=catalog_engine)
    with factory() as session:
        before = session.execute(text("SELECT id, platform_key FROM problems ORDER BY id")).all()
        report = SeedLoader(session, _clock()).load(SEED_DIR)
        after = session.execute(text("SELECT id, platform_key FROM problems ORDER BY id")).all()
    assert not report.changed and before == after
    assert get(activity_client, f"/problem-attempts/{attempt['id']}")["data"] == attempt


def test_seed_cannot_take_over_a_personal_problem(
    activity_client: TestClient, catalog_engine: Engine, tmp_path: Any
) -> None:
    post(
        activity_client,
        "/problems",
        {
            "platform": "LEETCODE",
            "platform_key": "zigzag-conversion",
            "title": "Zigzag Conversion",
            "difficulty": "EASY",
            "skills": [{"skill": "hashing.lookup_frequency", "mapping_weight_bp": 10000}],
        },
    )
    from app.services.seed_service import lock_seed_dir
    from tests.catalog_helpers import bump_version, copy_seed

    def add_same(raw: dict[str, Any]) -> None:
        bump_version(raw, "seed-v4")
        problems = raw["problem_catalog"]["problems"]
        problems.append(
            {**problems[0], "id": 900, "platform_key": "zigzag-conversion", "title": "Zigzag Conversion"}
        )

    seed = copy_seed(tmp_path, mutate=add_same)
    lock_seed_dir(seed)
    with sessionmaker(bind=catalog_engine)() as session, pytest.raises(SeedValidationError) as failure:
        SeedLoader(session, _clock()).load(seed)
    assert [i.code for i in failure.value.issues] == ["problems.conflicts_with_personal"]


# ------------------------------------------------------------------------------------------ determinism


def test_stored_observation_is_independent_of_ruleset_changes(
    activity_client: TestClient, monkeypatch: pytest.MonkeyPatch, catalog_engine: Engine
) -> None:
    attempt = record(activity_client, problem_id=27, outcome="FAIL", mistakes=["WRONG_PATTERN"])
    monkeypatch.setattr(RULESETS["v1"], "LEECH_LAPSES", 99)
    monkeypatch.setattr(RULESETS["v1"], "UNCERTAINTY", {"LOW": 0, "MEDIUM": 0, "HIGH": 0})
    assert get(activity_client, f"/problem-attempts/{attempt['id']}")["data"] == attempt
    with Session(catalog_engine) as session:
        columns = {c.name for c in ProblemAttempt.__table__.columns}
        assert session.scalar(select(func.count()).select_from(ProblemAttempt)) == 1
    assert not {"ruleset_version", "score", "level", "quality"} & columns  # raw facts only


def _clock() -> Any:
    from datetime import datetime

    from app.domain.clock import FixedClock
    from tests.conftest import FIXED_NOW

    return FixedClock(datetime.fromisoformat(FIXED_NOW))
