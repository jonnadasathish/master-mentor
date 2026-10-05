"""Seed validation against the REAL seed files, plus targeted mutations that must each be caught."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from app.domain.catalog.validate import ValidationResult, validate_seed
from tests.catalog_helpers import real_raw

PROFILE = "role_profile:backend_fullstack_sde2"


def skill(raw: dict[str, Any], key: str) -> dict[str, Any]:
    return next(s for s in raw["skill_graph"]["skills"] if s["key"] == key)


def mutated(mutate: Callable[[dict[str, Any]], None]) -> ValidationResult:
    raw, lock = real_raw()
    mutate(raw)
    return validate_seed(raw, lock)


def error_codes(result: ValidationResult) -> set[str]:
    return {i.code for i in result.errors}


def test_real_seed_is_valid_with_expected_counts() -> None:
    raw, lock = real_raw()
    result = validate_seed(raw, lock)
    assert result.errors == ()
    catalog = result.catalog
    assert catalog is not None
    assert catalog.seed_version == "seed-v1"
    assert (len(catalog.groups), len(catalog.skills)) == (22, 133)
    assert sum(len(s.prerequisites) for s in catalog.skills) == 134
    assert len(catalog.profiles) == 1 and len(catalog.profiles[0].targets) == 133
    assert sum(1 for t in catalog.profiles[0].targets if t.required) == 123
    assert (len(catalog.problems), sum(len(p.skills) for p in catalog.problems)) == (44, 77)
    assert (len(catalog.milestones), len(catalog.baseline)) == (18, 12)
    assert len(catalog.templates) == 86
    assert catalog.max_depth == 6


def test_validation_is_deterministic() -> None:
    raw, lock = real_raw()
    a, b = validate_seed(raw, lock), validate_seed(raw, lock)
    assert a.catalog_fingerprint == b.catalog_fingerprint and a.catalog == b.catalog


# --------------------------------------------------------------------------- skills / graph


def test_duplicate_skill() -> None:
    result = mutated(lambda r: r["skill_graph"]["skills"].append(dict(skill(r, "two_pointers.core"))))
    assert "skills.duplicate_key" in error_codes(result)
    assert result.catalog is None


def test_missing_prerequisite() -> None:
    def mutate(r: dict[str, Any]) -> None:
        skill(r, "dp.fundamentals")["prerequisites"].append({"skill": "dp.missing_basics", "min_score": 45})

    result = mutated(mutate)
    assert "graph.missing_node" in error_codes(result)
    assert any("dp.missing_basics" in i.message for i in result.errors)


def test_cycle_is_reported_with_path() -> None:
    def mutate(r: dict[str, Any]) -> None:
        skill(r, "recursion.fundamentals")["prerequisites"].append(
            {"skill": "dp.fundamentals", "min_score": 30}
        )

    result = mutated(mutate)
    cycle = [i for i in result.errors if i.code == "graph.cycle"]
    assert len(cycle) == 1
    assert "dp.fundamentals → recursion.fundamentals → dp.fundamentals" in cycle[0].message


def test_self_reference() -> None:
    result = mutated(
        lambda r: skill(r, "heap.top_k")["prerequisites"].append({"skill": "heap.top_k", "min_score": 30})
    )
    assert "graph.self_reference" in error_codes(result)


def test_missing_parent_and_invalid_component() -> None:
    def mutate(r: dict[str, Any]) -> None:
        skill(r, "heap.top_k")["parent"] = "dsa.nonexistent"
        r["skill_graph"]["groups"][0]["component"] = "frontend"

    codes = error_codes(mutated(mutate))
    assert {"skills.missing_parent", "skills.invalid_component"} <= codes


def test_missing_required_metadata() -> None:
    result = mutated(lambda r: skill(r, "heap.top_k").pop("name"))
    assert any(i.code == "seed.missing_field" and "'name'" in i.message for i in result.errors)


def test_invalid_min_score() -> None:
    result = mutated(lambda r: skill(r, "dp.fundamentals")["prerequisites"][0].update(min_score=50))
    assert "skills.invalid_min_score" in error_codes(result)


def test_required_skill_depending_on_optional_skill() -> None:
    def mutate(r: dict[str, Any]) -> None:
        skill(r, "heap.top_k")["prerequisites"].append({"skill": "bit_manipulation.core", "min_score": 30})

    assert "graph.required_depends_on_optional" in error_codes(mutated(mutate))


def test_depth_limit() -> None:
    def mutate(r: dict[str, Any]) -> None:
        # dp.tree has depth 4; a 3-skill chain on top reaches depth 7 > limit 6.
        previous = "dp.tree"
        for suffix in ("a", "b", "c"):
            key = f"dp.tree_chain_{suffix}"
            r["skill_graph"]["skills"].append(
                {**skill(r, "dp.tree"), "key": key, "prerequisites": [{"skill": previous, "min_score": 30}]}
            )
            previous = key

    result = mutated(mutate)
    deep = [i for i in result.errors if i.code == "graph.too_deep"]
    assert len(deep) == 1 and "dp.tree_chain_c" in deep[0].message


# --------------------------------------------------------------------------- role profile


def test_unknown_skill_in_role_profile() -> None:
    result = mutated(lambda r: r[PROFILE]["skill_tiers"]["T1"].append("ghost.skill"))
    assert "profile.unknown_skill" in error_codes(result)


def test_duplicate_skill_in_role_profile() -> None:
    result = mutated(lambda r: r[PROFILE]["skill_tiers"]["T2"].append("heap.top_k"))
    assert "profile.duplicate_skill" in error_codes(result)


def test_skill_without_tier() -> None:
    result = mutated(lambda r: r[PROFILE]["skill_tiers"]["T1"].remove("heap.top_k"))
    assert "profile.missing_skill" in error_codes(result)


@pytest.mark.parametrize("bad", [101, -1, "80"])
def test_invalid_target_score(bad: object) -> None:
    result = mutated(lambda r: r[PROFILE]["tiers"]["T1"].update(target=bad))
    assert error_codes(result) & {"seed.invalid_score", "seed.wrong_type"}


def test_floor_above_target_and_gate_above_target_mean() -> None:
    def mutate(r: dict[str, Any]) -> None:
        r[PROFILE]["tiers"]["T3"]["floor"] = 70  # target 65
        r[PROFILE]["components"][0]["gate"] = 79  # dsa target mean 75.66

    codes = error_codes(mutated(mutate))
    assert {"profile.floor_above_target", "profile.gate_above_target_mean"} <= codes


def test_weights_must_sum_to_100() -> None:
    assert "profile.weights" in error_codes(mutated(lambda r: r[PROFILE]["components"][0].update(weight=30)))


def test_unreachable_prerequisite_min_score() -> None:
    # math.number_basics is T4 (target 50); a min_score of 60 on it can never be satisfied.
    def mutate(r: dict[str, Any]) -> None:
        skill(r, "bit_manipulation.core")["prerequisites"].append(
            {"skill": "math.number_basics", "min_score": 60}
        )

    assert "profile.unreachable_prerequisite" in error_codes(mutated(mutate))


# --------------------------------------------------------------------------- problems


def test_broken_problem_mapping_unknown_skill() -> None:
    result = mutated(lambda r: r["problem_catalog"]["problems"][0]["skills"][0].update(skill="ghost.skill"))
    assert "problems.unknown_skill" in error_codes(result)


def test_problem_needs_exactly_one_primary_mapping() -> None:
    result = mutated(
        lambda r: r["problem_catalog"]["problems"][0]["skills"][1].update(mapping_weight_bp=10000)
    )
    assert "problems.primary_mapping" in error_codes(result)


def test_duplicate_problem_identity_and_invalid_difficulty() -> None:
    def mutate(r: dict[str, Any]) -> None:
        problems = r["problem_catalog"]["problems"]
        problems.append({**problems[0], "id": 999})
        problems[1]["difficulty"] = "IMPOSSIBLE"

    assert {"problems.duplicate_identity", "problems.invalid_difficulty"} <= error_codes(mutated(mutate))


# --------------------------------------------------------------------------- roadmap


def test_roadmap_unknown_and_duplicate_skill() -> None:
    def mutate(r: dict[str, Any]) -> None:
        track = r["roadmap"]["tracks"]["cs"]
        track[0]["skills"].append("ghost.skill")
        track[1]["skills"].append("db.indexing")  # already in CS-1

    assert {"roadmap.unknown_skill", "roadmap.duplicate_skill"} <= error_codes(mutated(mutate))


def test_roadmap_skill_missing_from_all_milestones() -> None:
    result = mutated(lambda r: r["roadmap"]["tracks"]["cs"][0]["skills"].remove("db.indexing"))
    assert "roadmap.missing_skill" in error_codes(result)


def test_roadmap_ordering_prerequisite_in_later_milestone() -> None:
    def mutate(r: dict[str, Any]) -> None:
        dsa = r["roadmap"]["tracks"]["dsa_coding"]
        dsa[0]["skills"].remove("recursion.fundamentals")
        dsa[2]["skills"].append("recursion.fundamentals")  # DSA-3, but trees.traversal (DSA-2) needs it

    result = mutated(mutate)
    assert "roadmap.ordering" in error_codes(result)
    assert any("introduced later in DSA-3" in i.message for i in result.errors)


def test_track_without_milestones() -> None:
    assert "roadmap.missing_milestone" in error_codes(
        mutated(lambda r: r["roadmap"]["tracks"].update(lld=[]))
    )


# --------------------------------------------------------------------------- mission templates


def template(r: dict[str, Any], key: str) -> dict[str, Any]:
    return next(t for t in r["mission_templates"]["templates"] if t["key"] == key)


def test_invalid_mission_template() -> None:
    def mutate(r: dict[str, Any]) -> None:
        template(r, "dsa.timed").update(stage="SPRINT")
        template(r, "cs.recall").update(minutes=0)
        template(r, "lld.guided").pop("pass_rule")
        template(r, "behavioral.timed").update(next_on_pass="NOWHERE")
        template(r, "cs.dbms_query_lab")["applies_to"].append("db.not_a_skill")

    codes = error_codes(mutated(mutate))
    assert {
        "templates.unknown_stage",
        "templates.invalid_duration",
        "seed.missing_field",
        "templates.broken_reference",
        "templates.unknown_skill",
    } <= codes


def test_unknown_template_component_and_lost_coverage() -> None:
    def mutate(r: dict[str, Any]) -> None:
        template(r, "dsa.explain").update(component="frontend")
        templates = r["mission_templates"]["templates"]
        templates[:] = [t for t in templates if t["key"] not in ("cs.explain",)]

    codes = error_codes(mutated(mutate))
    assert {"templates.unknown_component", "templates.coverage"} <= codes


# --------------------------------------------------------------------------- versioning


def test_seed_versions_must_match_across_files() -> None:
    assert "seed.version_mismatch" in error_codes(
        mutated(lambda r: r["roadmap"].update(seed_version="seed-v2"))
    )


def test_content_change_without_version_bump_fails() -> None:
    result = mutated(lambda r: r["problem_catalog"]["problems"][0].update(title="Two Sum (edited)"))
    lock_errors = [i for i in result.errors if i.code == "lock.changed_without_version_bump"]
    assert [i.where for i in lock_errors] == ["seed.lock.yaml: seed-v1.files.problem_catalog"]


def test_new_version_must_be_locked() -> None:
    def mutate(r: dict[str, Any]) -> None:
        for data in r.values():
            data["seed_version"] = "seed-v2"

    assert error_codes(mutated(mutate)) == {"lock.unlocked_version"}


def test_floats_are_rejected() -> None:
    result = mutated(lambda r: r[PROFILE]["components"][0].update(weight=25.0))
    assert "seed.float_value" in error_codes(result)
