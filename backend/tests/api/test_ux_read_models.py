"""Slice 9 read models: roadmap, skill detail extras, readiness change in write effects."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db


def test_roadmap_tracks_milestones_and_battery(activity_client: TestClient) -> None:
    data = get(activity_client, "/roadmap")["data"]
    tracks = {t["track"]: t for t in data["tracks"]}
    assert set(tracks) == {"dsa_coding", "cs", "lld", "system_design", "behavioral_project", "mock"}
    dsa = tracks["dsa_coding"]
    assert dsa["current_milestone"] == "DSA-1" and dsa["milestones"][0]["current"] is True
    assert dsa["milestones"][0]["required_done"] == 0 and dsa["milestones"][0]["required_total"] > 0
    assert any(x["text"].startswith("every T1 skill") for m in dsa["milestones"] for x in m["extra_exit"])
    assert data["baseline"] == {"done": 0, "total": 12, "next_item": "M0-B01", "calibration_mode": True}


def test_skill_detail_has_downstream_milestone_revisions_and_focus(activity_client: TestClient) -> None:
    post(activity_client, "/problem-attempts", SOLVED)  # Two Sum: canonical -> PROBLEM:1, patterns
    detail = get(activity_client, "/skills/dsa.complexity_analysis")["data"]
    assert "heap.top_k" in detail["dependents"]
    assert detail["milestone"]["key"] == "DSA-1"
    assert any(r["item_key"] == "CONCEPT:dsa.complexity_analysis" for r in detail["revision_items"])
    assert detail["focus"]["stage"] and detail["focus"]["template_key"]


def test_write_effects_carry_readiness_change(activity_client: TestClient) -> None:
    get(activity_client, "/readiness")
    effects = post(activity_client, "/problem-attempts", SOLVED)["effects"]
    change = effects["readiness_change"]
    assert (change["before"], change["after"]) == ("NOT_MEASURED", "NOT_MEASURED")
    assert set(change) == {"before", "after", "blockers_added", "blockers_removed"}
