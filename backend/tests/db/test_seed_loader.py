"""Seed loading: first load, idempotent reload, changed seed, failure before writes, determinism."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.clock import FixedClock
from app.models import AuditLog, CatalogLoad, Problem, RoadmapMilestoneSkill, RoleSkillTarget, Skill
from app.services.seed_service import (
    LoadReport,
    SeedLoader,
    SeedValidationError,
    lock_seed_dir,
    validate_seed_dir,
)
from tests.catalog_helpers import (
    SEED_DIR,
    bump_version,
    catalog_snapshot,
    clear_catalog,
    copy_seed,
    retire_learning_skill,
    retire_problem_skill,
    scrub_problem_refs,
)

pytestmark = pytest.mark.db
CLOCK = FixedClock(datetime(2026, 10, 4, 12, 0, tzinfo=UTC))
EXPECTED = {
    "skill_groups": 27,
    "skills": 161,
    "skill_prerequisites": 161,
    "role_profiles": 1,
    "role_skill_targets": 161,
    "problems": 137,
    "problem_skills": 242,
    "mission_templates": 96,
    "roadmap_milestones": 19,
    "roadmap_milestone_skills": 161,
    "baseline_items": 12,
}
# Learning catalog counts follow the content files (they grow as content is authored); derived from the
# validated catalog so this test checks that the loader writes exactly what was validated.
_LEARNING = validate_seed_dir(SEED_DIR).catalog
assert _LEARNING is not None
_TOPICS = [p for t in _LEARNING.learning.tracks for p in t.topics]
EXPECTED |= {
    "learning_tracks": len(_LEARNING.learning.tracks),
    "learning_topics": len(_TOPICS),
    "learning_topic_skills": sum(len(p.skills) for p in _TOPICS),
    "learning_content": len(_LEARNING.learning.content),
    "learning_content_skills": sum(len(c.skills) for c in _LEARNING.learning.content),
}
LEARNING_FILES = {f"learning:{path.stem}" for path in (SEED_DIR / "learning").glob("*.yaml")}


def load(session: Session, seed_dir: Path = SEED_DIR) -> LoadReport:
    return SeedLoader(session, CLOCK).load(seed_dir)


def test_first_load_into_clean_database(catalog_session: Session) -> None:
    report = load(catalog_session)
    assert report.changed
    assert {name: c.inserted for name, c in report.tables.items()} == EXPECTED
    assert report.catalog_load_id is not None
    current = catalog_session.scalar(select(CatalogLoad).order_by(CatalogLoad.id.desc()))
    assert current is not None and current.seed_version == "seed-v3"
    assert current.catalog_fingerprint == report.catalog_fingerprint
    assert (
        set(current.file_fingerprints_json)
        == {
            "mission_templates",
            "problem_catalog",
            "roadmap",
            "role_profile:backend_fullstack_sde2",
            "skill_graph",
        }
        | LEARNING_FILES
    )
    assert catalog_session.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_second_identical_load_is_a_no_op(catalog_session: Session) -> None:
    load(catalog_session)
    before = catalog_snapshot(catalog_session, include_ids=True)
    for _ in range(2):  # seed, seed, seed
        report = load(catalog_session)
        assert not report.changed
        assert report.catalog_load_id is None
        assert all(c.inserted == c.updated == c.deactivated == c.deleted == 0 for c in report.tables.values())
        assert {name: c.unchanged for name, c in report.tables.items()} == EXPECTED
    catalog_session.expire_all()
    assert catalog_snapshot(catalog_session, include_ids=True) == before  # identical, ids included
    assert catalog_session.scalar(select(func.count()).select_from(CatalogLoad)) == 1
    assert catalog_session.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_two_fresh_databases_get_identical_catalogs(catalog_engine: Engine) -> None:
    factory = sessionmaker(bind=catalog_engine, expire_on_commit=False)
    snapshots = []
    for _ in range(2):
        clear_catalog(catalog_engine)
        with factory() as session:
            load(session)
            snapshots.append(catalog_snapshot(session))
    assert snapshots[0] == snapshots[1]


def test_invalid_seed_fails_before_any_write(catalog_session: Session, tmp_path: Path) -> None:
    load(catalog_session)
    before = catalog_snapshot(catalog_session, include_ids=True)

    def corrupt(raw: dict[str, Any]) -> None:
        bump_version(raw, "seed-v4")
        raw["skill_graph"]["skills"][0]["prerequisites"].append({"skill": "ghost.skill", "min_score": 45})
        raw["problem_catalog"]["problems"][0]["title"] = "would be written if validation were skipped"

    seed = copy_seed(tmp_path, mutate=corrupt)
    with pytest.raises(SeedValidationError) as failure:
        load(catalog_session, seed)
    assert "graph.missing_node" in {i.code for i in failure.value.issues}
    catalog_session.expire_all()
    assert catalog_snapshot(catalog_session, include_ids=True) == before


def test_invalid_seed_on_empty_database_writes_nothing(catalog_session: Session, tmp_path: Path) -> None:
    seed = copy_seed(
        tmp_path, mutate=lambda raw: raw["roadmap"]["tracks"]["cs"][0]["skills"].append("ghost.x")
    )
    with pytest.raises(SeedValidationError):
        load(catalog_session, seed)
    assert catalog_session.scalar(select(func.count()).select_from(Skill)) == 0
    assert catalog_session.scalar(select(func.count()).select_from(CatalogLoad)) == 0


def test_changed_seed_updates_deactivates_and_records_new_version(
    catalog_session: Session, tmp_path: Path
) -> None:
    load(catalog_session)
    skill_ids_before = {s.skill_key: s.id for s in catalog_session.scalars(select(Skill))}

    retired_problems: list[int] = []

    def change(raw: dict[str, Any]) -> None:
        bump_version(raw, "seed-v4")
        problems = raw["problem_catalog"]["problems"]
        problems[0]["title"] = "Two Sum (renamed)"
        problems[:] = [p for p in problems if p["platform_key"] != "single-number"]  # id 44 retired
        problems.append(
            {
                **problems[1],
                "id": 900,
                "platform_key": "zigzag-conversion",
                "title": "Zigzag Conversion",
                "is_canonical": False,
            }
        )
        # retire an optional skill everywhere it is referenced
        raw["skill_graph"]["skills"][:] = [
            s for s in raw["skill_graph"]["skills"] if s["key"] != "math.number_basics"
        ]
        raw["role_profile:backend_fullstack_sde2"]["skill_tiers"]["T4"].remove("math.number_basics")
        raw["roadmap"]["tracks"]["dsa_coding"][2]["skills"].remove("math.number_basics")
        retire_learning_skill(raw, "math.number_basics")
        retired_problems.extend(retire_problem_skill(raw, "math.number_basics"))
        scrub_problem_refs(raw, [*retired_problems, 44])

    seed = copy_seed(tmp_path, mutate=change)
    lock_seed_dir(seed)
    report = load(catalog_session, seed)

    assert report.changed and report.seed_version == "seed-v4"
    assert report.tables["problems"].inserted == 1
    assert report.tables["problems"].deactivated == 1 + len(
        retired_problems
    )  # single-number + the skill's own
    assert report.tables["skills"].deactivated == 1
    assert report.tables["role_skill_targets"].deleted == 1
    assert report.tables["roadmap_milestone_skills"].deleted == 1

    catalog_session.expire_all()
    retired = catalog_session.scalar(select(Skill).where(Skill.skill_key == "math.number_basics"))
    assert retired is not None and retired.active is False  # kept for history, never deleted
    assert {
        s.skill_key: s.id for s in catalog_session.scalars(select(Skill))
    } == skill_ids_before  # stable ids
    assert catalog_session.get(Problem, 1).title == "Two Sum (renamed)"  # type: ignore[union-attr]
    assert catalog_session.get(Problem, 44).active is False  # type: ignore[union-attr]
    assert catalog_session.scalar(select(func.count()).select_from(RoleSkillTarget)) == 160
    assert catalog_session.scalar(select(func.count()).select_from(RoadmapMilestoneSkill)) == 160
    loads = catalog_session.scalars(select(CatalogLoad).order_by(CatalogLoad.id)).all()
    assert [entry.seed_version for entry in loads] == ["seed-v3", "seed-v4"]

    # Loading the changed seed again is a no-op too.
    assert not load(catalog_session, seed).changed
