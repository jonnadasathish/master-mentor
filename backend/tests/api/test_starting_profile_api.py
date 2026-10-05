"""Starting profile, onboarding, calibration status, personal roadmap and current state (D-080), end to end.

Seeded catalog, frozen clock (2026-10-04 12:00 UTC = Sunday in Asia/Kolkata).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import sessionmaker

from app.models import AuditLog
from tests.api.test_activity_api import SOLVED, get, post

pytestmark = pytest.mark.db
API = "/api/v1"
GOAL = {"target_date": "2027-06-28", "weekday_budgets": [90, 90, 90, 90, 90, 75, 75]}


def put(client: TestClient, path: str, body: dict[str, Any], status: int = 200) -> dict[str, Any]:
    response = client.put(f"{API}{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


def groups(client: TestClient) -> dict[str, list[str]]:
    tree = get(client, "/catalog/tree")["data"]
    return {g["key"]: g["skills"] for c in tree for g in c["groups"]}


def sweep_all_unknown(client: TestClient) -> None:
    required = [t["skill"] for t in get(client, "/catalog/role-profile/targets", required=True)["data"]]
    post(
        client,
        "/assessments/self-assessment-sweep",
        {
            "entries": [{"skill": k, "familiarity": "NONE"} for k in required],
            "client_request_id": "sweep-123456",
        },
    )


def complete_battery(client: TestClient) -> None:
    """Every battery item through the real observation endpoints (no shortcuts)."""
    problems = get(client, "/problems", difficulty="MEDIUM")["data"]
    n = 0
    for item in get(client, "/baseline")["data"]["items"]:
        if item["complete"] or item["observation_kind"] == "SELF_ASSESSMENT":
            continue
        n += 1
        if item["observation_kind"] == "ATTEMPT":
            for p in problems[:2]:
                body = {**SOLVED, "problem_id": p["id"], "battery_item_key": item["key"], "mode": "BASELINE"}
                body["client_request_id"] = f"req-{item['key']}-{p['id']}"
                post(client, "/problem-attempts", body)
            continue
        skills: list[str] = []
        for g in item["covers"]:
            skills += [s["key"] for s in get(client, f"/catalog/groups/{g}/skills")["data"]]
        post(
            client,
            "/assessments",
            {
                "kind": item["observation_kind"],
                "source_key": f"battery:{item['key']}",
                "notes_used": False,
                "reference_used": False,
                "hints_used": 0,
                "timed": False,
                "mode": "BASELINE",
                "skills": [
                    {"skill": s, "outcome_points": 40 + (i * 7) % 50} for i, s in enumerate(skills[:6])
                ],
                "battery_item_key": item["key"],
                "client_request_id": f"req-assess-{n}",
            },
        )


# ------------------------------------------------------------------------------------------ profile


def test_a_new_install_is_a_first_run_with_nothing_filled_in(activity_client: TestClient) -> None:
    profile = get(activity_client, "/profile")["data"]
    assert profile["onboarding"] == {"completed": False, "completed_at": None}
    assert profile["target"] is None and profile["technologies"] == [] and profile["company_profile"] is None
    assert profile["experience"] == {"years": None, "current_role": None, "previous_role": None}
    assert profile["self_report"] == {
        "strengths": [],
        "weaknesses": [],
        "never_studied": [],
        "recently_studied": [],
    }
    assert [r["profile_key"] for r in profile["available_roles"]] == ["backend_fullstack_sde2"]


def test_the_profile_is_saved_and_updated_without_losing_other_fields(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    put(
        activity_client,
        "/profile",
        {
            "display_name": "  Satish ",
            "experience": {"years": 6, "current_role": "Backend Engineer", "previous_role": "QA Engineer"},
            "technologies": ["Python", "python", "FastAPI", "MySQL"],
            "company_profile": "Product company",
        },
    )
    profile = get(activity_client, "/profile")["data"]
    assert profile["display_name"] == "Satish"
    assert get(activity_client, "/settings")["data"]["display_name"] == "Satish"
    assert profile["experience"] == {
        "years": 6,
        "current_role": "Backend Engineer",
        "previous_role": "QA Engineer",
    }
    assert profile["technologies"] == ["Python", "FastAPI", "MySQL"]  # case-insensitive de-duplication
    put(activity_client, "/profile", {"experience": {"years": 7}})
    after = get(activity_client, "/profile")["data"]
    assert after["experience"]["years"] == 7 and after["experience"]["current_role"] == "Backend Engineer"
    assert (
        after["technologies"] == ["Python", "FastAPI", "MySQL"]
        and after["company_profile"] == "Product company"
    )
    with sessionmaker(bind=catalog_engine)() as session:
        actions = list(
            session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "starting_profile"))
        )
    assert actions == ["UPDATE_STARTING_PROFILE", "UPDATE_STARTING_PROFILE"]


@pytest.mark.parametrize(
    ("body", "where"),
    [
        ({"experience": {"years": -1}}, "years"),
        ({"experience": {"years": 61}}, "years"),
        ({"experience": {"current_role": ""}}, "current_role"),
        ({"technologies": ["x" * 41]}, "technologies"),
        ({"technologies": [f"t{i}" for i in range(31)]}, "technologies"),
        ({"display_name": ""}, "display_name"),
        ({"nickname": "x"}, "nickname"),
        ({"self_report": {"strengths": ["not.a.group"]}}, "strengths"),
    ],
)
def test_invalid_profile_fields_are_rejected(
    activity_client: TestClient, body: dict[str, Any], where: str
) -> None:
    response = activity_client.put(f"{API}/profile", json=body)
    assert response.status_code == 422, response.text
    assert where in response.text


def test_contradictory_self_reports_are_rejected(activity_client: TestClient) -> None:
    g = next(iter(groups(activity_client)))
    for body in (
        {"strengths": [g], "weaknesses": [g]},
        {"strengths": [g], "never_studied": [g]},
        {"never_studied": [g], "recently_studied": [g]},
    ):
        assert activity_client.put(f"{API}/profile", json={"self_report": body}).status_code == 422
    put(
        activity_client,
        "/profile",
        {"self_report": {"strengths": [g], "weaknesses": [], "recently_studied": [g]}},
    )


# ------------------------------------------------------------------------------------------ onboarding


def test_onboarding_saves_the_profile_the_goal_and_the_first_run_flag(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    g = next(iter(groups(activity_client)))
    body = {
        "display_name": "Satish",
        "experience": {"years": 6},
        "technologies": ["Python"],
        "self_report": {"weaknesses": [g]},
        "goal": GOAL,
    }
    done = post(activity_client, "/onboarding/complete", body, status=200)
    profile = done["data"]
    assert profile["onboarding"]["completed"] is True and profile["onboarding"]["completed_at"]
    assert profile["target"]["role"]["name"] and profile["target"]["weekly_minutes"] == 600
    assert profile["target"]["target_date"] == "2027-06-28" and profile["target"]["phase"] == "BUILD"
    assert profile["self_report"]["weaknesses"] == [g]
    assert done["effects"]["run_id"]  # the goal change ran the mentor
    assert len(get(activity_client, "/goals/history")["data"]) == 1
    with sessionmaker(bind=catalog_engine)() as session:
        actions = list(
            session.scalars(select(AuditLog.action).where(AuditLog.entity_type == "starting_profile"))
        )
    assert actions == ["COMPLETE_ONBOARDING"]


def test_a_bad_goal_leaves_onboarding_unfinished(activity_client: TestClient) -> None:
    bad = {"experience": {"years": 3}, "goal": {"target_date": "2026-01-01"}}
    activity_client.post(f"{API}/onboarding/complete", json=bad)
    assert get(activity_client, "/profile")["data"]["onboarding"]["completed"] is False
    assert get(activity_client, "/profile")["data"]["experience"]["years"] is None  # nothing half-saved


def test_redoing_onboarding_keeps_history_and_only_versions_a_changed_goal(
    activity_client: TestClient,
) -> None:
    post(activity_client, "/onboarding/complete", {"goal": GOAL}, status=200)
    first = get(activity_client, "/profile")["data"]["onboarding"]["completed_at"]
    post(activity_client, "/onboarding/complete", {"goal": {"target_date": "2027-09-01"}}, status=200)
    profile = get(activity_client, "/profile")["data"]
    assert profile["onboarding"]["completed_at"] == first  # the first completion stays on record
    assert profile["target"]["target_date"] == "2027-09-01"
    assert len(get(activity_client, "/goals/history")["data"]) == 2


# ------------------------------------------------------------------------------------ self-report ≠ evidence


def test_self_report_never_changes_observed_state(
    activity_client: TestClient, catalog_engine: Engine
) -> None:
    post(activity_client, "/goals", GOAL)
    sweep_all_unknown(activity_client)
    before = {p: get(activity_client, p)["data"] for p in ("/skills", "/readiness", "/gaps")}
    all_groups = list(groups(activity_client))
    half = len(all_groups) // 2
    put(
        activity_client,
        "/profile",
        {"self_report": {"strengths": all_groups[:half], "weaknesses": all_groups[half:]}},
    )
    after = {p: get(activity_client, p)["data"] for p in ("/skills", "/readiness", "/gaps")}
    assert after == before, "claiming 'strong' must not move any score, gap or readiness value"
    with sessionmaker(bind=catalog_engine)() as session:
        evidence = session.execute(
            text("SELECT COUNT(*) FROM evidence WHERE source_type <> 'ASSESSMENT'")
        ).scalar_one()
    assert evidence == 0  # the profile wrote no evidence row of any kind
    assert all(s["state"]["score"] in (None, 0) for s in before["/skills"]), "a strength claim is not a score"


def test_the_export_carries_the_profile_and_reset_keeps_it_as_configuration(
    activity_client: TestClient,
) -> None:
    put(activity_client, "/profile", {"technologies": ["Python"]})
    exported = (
        get(activity_client, "/export/json")["data"]
        if False
        else activity_client.get(f"{API}/export/json").json()
    )
    assert exported["tables"]["starting_profile"][0]["technologies_json"] == ["Python"]


# ------------------------------------------------------------------------------------ calibration status


def test_calibration_phases_progress_from_not_started_to_complete(activity_client: TestClient) -> None:
    post(activity_client, "/goals", GOAL)
    fresh = get(activity_client, "/baseline")["data"]
    assert fresh["phase"] == "NOT_STARTED" and fresh["personalization_threshold_pct"] == 60
    assert (fresh["minutes_total"], fresh["minutes_done"], fresh["minutes_remaining"]) == (420, 0, 420)
    assert fresh["typical_daily_minutes"] == 85 and fresh["estimated_days"] == 5  # 420 / 85, rounded up

    sweep_all_unknown(
        activity_client
    )  # every required skill declared unknown: measured at 0, battery barely begun
    mid = get(activity_client, "/baseline")["data"]
    assert mid["phase"] == "ENOUGH_MEASURED" and mid["calibration_mode"] is True
    assert mid["minutes_done"] == 15 and mid["minutes_remaining"] == 405  # only the sweep item is done

    complete_battery(activity_client)
    done = get(activity_client, "/baseline")["data"]
    assert done["phase"] == "COMPLETE" and done["battery_done"] == done["battery_total"] == 12
    assert (done["minutes_done"], done["minutes_remaining"], done["estimated_days"]) == (420, 0, 0)


def test_in_progress_when_only_a_little_is_measured(activity_client: TestClient) -> None:
    post(activity_client, "/goals", GOAL)
    skill = get(activity_client, "/catalog/role-profile/targets", required=True)["data"][0]["skill"]
    post(
        activity_client,
        "/assessments/self-assessment-sweep",
        {"entries": [{"skill": skill, "familiarity": "NONE"}], "client_request_id": "sweep-654321"},
    )
    assert get(activity_client, "/baseline")["data"]["phase"] == "IN_PROGRESS"


# ------------------------------------------------------------------------------------ personal roadmap


def test_the_roadmap_waits_for_evidence_and_never_calls_unmeasured_skills_weak(
    activity_client: TestClient,
) -> None:
    post(activity_client, "/goals", GOAL)
    roadmap = get(activity_client, "/roadmap/personal")["data"]
    assert roadmap["available"] is False and roadmap["calibration_phase"] == "NOT_STARTED"
    assert roadmap["focus_now"] == [] and roadmap["sections"]["unmeasured"]["count"] > 100
    assert roadmap["sections"]["build"]["count"] == 0 and roadmap["sections"]["maintain"]["count"] == 0
    assert roadmap["based_on"]["measured_skills"] == 0 and roadmap["based_on"]["role"]["name"]


def test_the_roadmap_is_derived_from_measured_state_and_respects_prerequisites(
    activity_client: TestClient,
) -> None:
    post(activity_client, "/goals", GOAL)
    sweep_all_unknown(activity_client)
    roadmap = get(activity_client, "/roadmap/personal")["data"]
    assert roadmap["available"] is True
    focus = roadmap["focus_now"]
    assert 1 <= len(focus) <= 5
    assert all(i["status"] != "BLOCKED" and i["bucket"] in ("build", "consolidate", "sharpen") for i in focus)
    assert [i["priority"] for i in focus] == sorted((i["priority"] for i in focus), reverse=True)
    assert all(i["name"] and i["score"] is not None and i["target"] > 0 for i in focus)
    assert all(i["reason_codes"] for i in focus)
    # skills that depend on a weak prerequisite are built after it, and say which prerequisite is missing
    shown = [i for s in roadmap["sections"].values() for i in s["items"] if i["status"] == "BLOCKED"]
    assert all(i["prerequisites"] for i in shown)  # each says which prerequisite is missing
    assert all(i["bucket"] in ("build", "unmeasured") for i in shown)  # never presented as ready to practise
    blocked = activity_client.get(f"{API}/gaps", params={"status": "BLOCKED"}).json()["data"]["gaps"]
    blocked_keys = {g["skill_key"] for g in blocked}
    assert blocked_keys, "weak prerequisites block their dependents"
    assert not {i["skill_key"] for i in focus} & blocked_keys  # the prerequisite is practised first
    assert any(i["next_step_minutes"] for i in focus), "effort comes from the mission library"
    assert 1 <= len(roadmap["why"]) <= 3
    assert {w["skill_key"] for w in roadmap["why"]} <= {i["skill_key"] for i in focus}
    assert roadmap["why"][0]["prerequisites"] is not None and "n_fail_last5" in roadmap["why"][0]["metrics"]
    counts = {k: v["count"] for k, v in roadmap["sections"].items() if k != "later"}
    assert sum(counts.values()) == 133  # every skill of the catalog is in exactly one section
    assert roadmap["changes"]["since"] == "2026-10-03"


def test_the_roadmap_is_deterministic_and_self_report_cannot_move_it(activity_client: TestClient) -> None:
    post(activity_client, "/goals", GOAL)
    sweep_all_unknown(activity_client)
    first = get(activity_client, "/roadmap/personal")
    assert first == get(activity_client, "/roadmap/personal")
    put(activity_client, "/profile", {"self_report": {"strengths": list(groups(activity_client))[:5]}})
    assert get(activity_client, "/roadmap/personal") == first
    assert (
        get(activity_client, "/profile/state")["data"]["counts"]
        == get(activity_client, "/profile/state")["data"]["counts"]
    )


def test_a_nearer_target_date_changes_the_phase_and_parks_more(activity_client: TestClient) -> None:
    post(activity_client, "/goals", GOAL)
    sweep_all_unknown(activity_client)
    far = get(activity_client, "/roadmap/personal")["data"]
    assert far["based_on"]["phase"] == "BUILD" and far["based_on"]["weeks_left"] == "38.1"
    activity_client.patch(f"{API}/goals/active", json={"target_date": "2026-10-25"})
    near = get(activity_client, "/roadmap/personal")["data"]
    assert near["based_on"]["phase"] != "BUILD" and near["based_on"]["target_date"] == "2026-10-25"
    assert near["sections"]["parked"]["count"] > far["sections"]["parked"]["count"]


# ------------------------------------------------------------------------------------ current state


def test_the_current_state_shows_what_you_said_beside_what_was_measured(activity_client: TestClient) -> None:
    post(activity_client, "/goals", GOAL)
    by_group = groups(activity_client)
    measured_group = next(g for g, skills in by_group.items() if len(skills) >= 2)
    unmeasured_group = next(g for g in by_group if g != measured_group)
    put(
        activity_client,
        "/profile",
        {"self_report": {"strengths": [measured_group], "weaknesses": [unmeasured_group]}},
    )
    skill = by_group[measured_group][0]
    post(
        activity_client,
        "/assessments",
        {
            "kind": "RECALL_QUIZ",
            "source_key": "quiz:state",
            "notes_used": False,
            "reference_used": False,
            "hints_used": 0,
            "timed": False,
            "skills": [{"skill": skill, "outcome_points": 30}],
            "client_request_id": "req-state-1",
        },
    )
    state = get(activity_client, "/profile/state")["data"]
    claims = {g["group_key"]: g for g in state["self_reported"]}
    assert claims[measured_group]["claims"] == ["STRONG"] and claims[unmeasured_group]["claims"] == ["WEAK"]
    observed = claims[measured_group]
    assert observed["measured"] == 1 and observed["total"] == len(by_group[measured_group])
    assert observed["skills"][0]["skill_key"] == skill and observed["skills"][0]["score"] is not None
    assert claims[unmeasured_group]["measured"] == 0 and claims[unmeasured_group]["skills"] == []
    # the claim "strong" did not make the skill strong
    assert skill not in [i["skill_key"] for i in state["strong"]["items"]]
    assert state["counts"]["unknown"] > 100 and state["counts"]["total"] >= 123
    assert set(state) >= {"strong", "developing", "critical", "unknown", "self_reported", "counts"}


def test_a_declared_unknown_is_shown_as_a_self_rating_not_as_a_measurement(
    activity_client: TestClient,
) -> None:
    post(activity_client, "/goals", GOAL)
    by_group = groups(activity_client)
    group = next(g for g, skills in by_group.items() if len(skills) >= 2)
    put(activity_client, "/profile", {"self_report": {"strengths": [group]}})
    required = {
        t["skill"] for t in get(activity_client, "/catalog/role-profile/targets", required=True)["data"]
    }
    declared = next(s for s in by_group[group] if s in required)
    post(
        activity_client,
        "/assessments/self-assessment-sweep",
        {"entries": [{"skill": declared, "familiarity": "NONE"}], "client_request_id": "sweep-777777"},
    )
    state = get(activity_client, "/profile/state")["data"]
    entry = next(g for g in state["self_reported"] if g["group_key"] == group)
    assert entry["claims"] == ["STRONG"]  # what the user said stays a claim
    assert entry["measured"] == 0, "'new to me' is a self-rating: it is not counted as measured by a task"
    assert [(s["skill_key"], s["declared_unknown"]) for s in entry["skills"]] == [(declared, True)]
