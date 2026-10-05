"""Catalog read API over a test DB loaded with the real seed."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db
API = "/api/v1/catalog"


def ok(client: TestClient, path: str, **params: Any) -> dict[str, Any]:
    response = client.get(f"{API}{path}", params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert body["meta"]["seed_version"] == "seed-v1"
    return body


def test_summary_exposes_versions_fingerprints_and_counts(seeded_client: TestClient) -> None:
    data = ok(seeded_client, "")["data"]
    assert data["seed_version"] == "seed-v1" and len(data["catalog_fingerprint"]) == 64
    assert data["versions"]["catalog_version"].startswith("seed-v1+")
    assert set(data["versions"]) == {
        "catalog_version",
        "skill_graph_version",
        "role_profile_version",
        "problem_catalog_version",
        "mission_template_version",
        "roadmap_version",
    }
    assert data["counts"]["skills"] == 133 and data["counts"]["mission_templates"] == 86
    assert data["loaded_at"].endswith("Z") or data["loaded_at"].endswith("+00:00")


def test_skill_list_and_filters(seeded_client: TestClient) -> None:
    body = ok(seeded_client, "/skills")
    assert body["meta"]["count"] == 133 and body["data"][0]["key"] == "python.core_syntax"  # seed order
    assert ok(seeded_client, "/skills", component="lld")["meta"]["count"] == 6
    assert ok(seeded_client, "/skills", tier="T1")["meta"]["count"] == 35
    assert ok(seeded_client, "/skills", group="cs.dbms")["meta"]["count"] == 8


def test_skill_detail(seeded_client: TestClient) -> None:
    data = ok(seeded_client, "/skills/dp.fundamentals")["data"]
    assert (
        data["tier"],
        data["importance"],
        data["target_score"],
        data["floor_score"],
        data["required"],
    ) == (
        "T1",
        100,
        80,
        65,
        True,
    )
    assert [p["key"] for p in data["prerequisites"]] == ["recursion.fundamentals"]
    assert data["prerequisites"][0]["min_score"] == 60
    assert "dp.knapsack_subset" in [d["key"] for d in data["dependents"]]
    assert data["milestone"] == {"key": "DSA-3", "name": "Advanced graphs, tries, DP", "track": "dsa_coding"}


def test_prerequisites_direct_and_transitive(seeded_client: TestClient) -> None:
    direct = ok(seeded_client, "/skills/sliding_window.core/prerequisites")["data"]
    assert [(p["key"], p["min_score"]) for p in direct["prerequisites"]] == [
        ("two_pointers.core", 45),
        ("hashing.lookup_frequency", 45),
    ]
    deep = ok(seeded_client, "/skills/sliding_window.core/prerequisites", transitive="true")["data"]
    keys = [p["key"] for p in deep["prerequisites"]]
    assert {"arrays.traversal", "python.core_syntax", "python.collections"} <= set(keys)
    assert max(p["depth"] for p in deep["prerequisites"]) == 3


def test_tree_and_group_children(seeded_client: TestClient) -> None:
    tree = ok(seeded_client, "/tree")["data"]
    assert [c["component"] for c in tree] == [
        "dsa",
        "coding",
        "cs",
        "lld",
        "system_design",
        "behavioral",
        "project",
    ]
    assert sum(len(g["skills"]) for c in tree for g in c["groups"]) == 133
    assert ok(seeded_client, "/groups/lld.design/skills")["meta"]["count"] == 6


def test_role_profile_and_targets(seeded_client: TestClient) -> None:
    profile = ok(seeded_client, "/role-profile")["data"]
    assert profile["profile_key"] == "backend_fullstack_sde2"
    assert profile["tier_counts"] == {"T1": 35, "T2": 56, "T3": 32, "T4": 10}
    assert profile["required_skill_count"] == 123
    assert len(profile["critical_skills"]) == 35
    assert sum(c["weight"] for c in profile["config"]["components"]) == 100
    assert ok(seeded_client, "/role-profile/targets", required="true")["meta"]["count"] == 123
    assert ok(seeded_client, "/role-profile/targets", required="false")["meta"]["count"] == 10


def test_roadmap(seeded_client: TestClient) -> None:
    data = ok(seeded_client, "/roadmap")["data"]
    assert [t["track"] for t in data["tracks"]] == [
        "dsa_coding",
        "cs",
        "lld",
        "system_design",
        "behavioral_project",
        "mock",
    ]
    assert sum(len(t["milestones"]) for t in data["tracks"]) == 18
    assert sum(len(m["skills"]) for t in data["tracks"] for m in t["milestones"]) == 133
    assert len(data["baseline_items"]) == 12 and data["baseline_total_minutes"] == 420
    assert ok(seeded_client, "/roadmap/milestones/LLD-3")["data"]["skills"] == ["lld.machine_coding"]


def test_problems(seeded_client: TestClient) -> None:
    assert ok(seeded_client, "/problems")["meta"]["count"] == 44
    by_skill = ok(seeded_client, "/problems", skill="graph.traversal")["data"]
    assert [p["id"] for p in by_skill] == [27, 28, 29, 30, 31]  # 4 primary + rotting-oranges (secondary)
    assert ok(seeded_client, "/problems", difficulty="HARD")["meta"]["count"] == 4
    one = ok(seeded_client, "/problems/42")["data"]
    assert one["platform_key"] == "lru-cache"
    assert [s["skill"] for s in one["skills"] if s["primary"]] == ["design_ds.core"]
    assert ok(seeded_client, "/problems/by-key/LEETCODE/two-sum")["data"]["id"] == 1


def test_mission_template_listing_and_resolution(seeded_client: TestClient) -> None:
    assert ok(seeded_client, "/mission-templates")["meta"]["count"] == 86
    assert ok(seeded_client, "/mission-templates", component="dsa", stage="TIMED")["meta"]["count"] == 1
    drill = ok(
        seeded_client,
        "/mission-templates/resolve",
        component="system_design",
        stage="TIMED",
        skill="sd.capacity_estimation",
    )["data"]
    assert (drill["level"], drill["template"]["key"]) == (2, "system_design.drill")
    fallback = ok(
        seeded_client,
        "/mission-templates/resolve",
        component="dsa",
        stage="THINK_ALOUD",
        skill="trees.traversal",
    )["data"]
    assert (fallback["level"], fallback["template"]["key"]) == (5, "generic.think_aloud")


@pytest.mark.parametrize(
    ("path", "params", "status", "code"),
    [
        ("/skills/ghost.skill", {}, 404, "NOT_FOUND"),
        ("/problems/9999", {}, 404, "NOT_FOUND"),
        ("/skills", {"component": "frontend"}, 422, "VALIDATION_ERROR"),
        ("/skills", {"tier": "T9"}, 422, "VALIDATION_ERROR"),
        (
            "/mission-templates/resolve",
            {"component": "dsa", "stage": "NAP", "skill": "heap.top_k"},
            422,
            "VALIDATION_ERROR",
        ),
    ],
)
def test_errors_use_the_envelope(
    seeded_client: TestClient, path: str, params: dict[str, str], status: int, code: str
) -> None:
    response = seeded_client.get(f"{API}{path}", params=params)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_catalog_not_loaded_is_a_409(db_client_empty_catalog: TestClient) -> None:
    response = db_client_empty_catalog.get(f"{API}/skills")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE"


def test_health_reports_loaded_seed_version(seeded_client: TestClient) -> None:
    assert seeded_client.get("/api/v1/health").json()["data"]["seed_version"] == "seed-v1"
