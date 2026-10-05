"""Catalog test helpers: seed copies/mutations and a natural-key snapshot of the catalog tables."""

from __future__ import annotations

import copy
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.seed_files import read_seed
from app.models import (
    BaselineItem,
    CatalogLoad,
    MissionTemplate,
    Problem,
    ProblemSkill,
    RoadmapMilestone,
    RoadmapMilestoneSkill,
    RoleProfile,
    RoleSkillTarget,
    Skill,
    SkillGroup,
    SkillPrerequisite,
)

SEED_DIR = Path(get_settings().seed_dir)
FILES = {
    "skill_graph": "skills.yaml",
    "problem_catalog": "problems.yaml",
    "roadmap": "roadmap.yaml",
    "mission_templates": "mission_templates.yaml",
}
KEEP_TABLES = {"alembic_version", "app_settings", "starting_profile"}


def real_raw() -> tuple[dict[str, Any], dict[str, Any] | None]:
    raw, lock = read_seed(SEED_DIR)
    return copy.deepcopy(raw), copy.deepcopy(lock)


def copy_seed(tmp_path: Path, mutate: Callable[[dict[str, Any]], None] | None = None) -> Path:
    """Copy the real seed into tmp_path; optionally mutate the parsed files (role -> data), rewrite them."""
    target = tmp_path / "seed"
    shutil.copytree(SEED_DIR, target)
    if mutate is not None:
        raw, _ = read_seed(target)
        mutate(raw)
        for role, data in raw.items():
            name = FILES.get(role) or _role_file(role)
            (target / name).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


def _role_file(role: str) -> str:
    folder = "learning" if role.startswith("learning:") else "role_profiles"
    return f"{folder}/{role.split(':', 1)[1]}.yaml"


def retire_learning_skill(raw: dict[str, Any], skill: str) -> None:
    """Remove a skill from the curriculum and drop content that only teaches it (for skill-retirement
    tests)."""
    for track in raw["learning:curriculum"]["tracks"]:
        for topic in track["topics"]:
            if skill in topic["skills"]:
                topic["skills"].remove(skill)
        track["topics"][:] = [t for t in track["topics"] if t["skills"]]
    for role, data in raw.items():
        if role.startswith("learning:") and role != "learning:curriculum":
            for item in data["content"]:
                if skill in item["skills"]:
                    item["skills"].remove(skill)
            data["content"][:] = [c for c in data["content"] if c["skills"]]


def bump_version(raw: dict[str, Any], version: str) -> None:
    for data in raw.values():
        data["seed_version"] = version


def clear_catalog(engine: Engine) -> None:
    with engine.begin() as connection:
        existing = set(inspect(connection).get_table_names())
        # Test-only cleanup. Self-referencing FKs (corrections) make a plain DELETE order-dependent.
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        # Every table except the migration marker and the bootstrap settings row (future slices included).
        for table in sorted(existing - KEEP_TABLES):
            connection.execute(text(f"DELETE FROM `{table}`"))
        if "app_settings" in existing:  # tests may PATCH settings: restore the bootstrap values
            connection.execute(
                text("UPDATE app_settings SET timezone = :tz, display_name = 'Owner' WHERE id = 1"),
                {"tz": get_settings().app_default_timezone},
            )
        if "starting_profile" in existing:  # tests may save a profile: back to the bootstrap row (first run)
            connection.execute(
                text(
                    "UPDATE starting_profile SET onboarding_completed_at = NULL, experience_years = NULL, "
                    "current_role = NULL, previous_role = NULL, company_profile = NULL, "
                    "technologies_json = JSON_ARRAY(), "
                    "self_report_json = JSON_OBJECT('strengths', JSON_ARRAY(), 'weaknesses', JSON_ARRAY(), "
                    "'never_studied', JSON_ARRAY(), 'recently_studied', JSON_ARRAY()) WHERE id = 1"
                )
            )
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def catalog_snapshot(session: Session, *, include_ids: bool = False) -> dict[str, Any]:
    """Catalog state keyed by natural keys (surrogate ids optional; load timestamps excluded)."""

    def row(obj: Any, drop: tuple[str, ...] = ()) -> dict[str, Any]:
        cols = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
        if not include_ids:
            cols = {
                k: v for k, v in cols.items() if k not in ("id", "group_id", "profile_id", "milestone_id")
            }
        return {k: v for k, v in cols.items() if k not in drop}

    skill_key = {s.id: s.skill_key for s in session.query(Skill)}
    group_key = {g.id: g.group_key for g in session.query(SkillGroup)}
    profile_key = {p.id: p.profile_key for p in session.query(RoleProfile)}
    milestone_key = {m.id: m.milestone_key for m in session.query(RoadmapMilestone)}
    return {
        "skill_groups": {g.group_key: row(g) for g in session.query(SkillGroup)},
        "skills": {s.skill_key: row(s) | {"group": group_key[s.group_id]} for s in session.query(Skill)},
        "skill_prerequisites": {
            (skill_key[p.skill_id], skill_key[p.prereq_skill_id]): (p.min_score, p.position)
            for p in session.query(SkillPrerequisite)
        },
        "role_profiles": {p.profile_key: row(p) for p in session.query(RoleProfile)},
        "role_skill_targets": {
            (profile_key[t.profile_id], skill_key[t.skill_id]): (
                t.tier,
                t.importance,
                t.target_score,
                t.floor_score,
            )
            for t in session.query(RoleSkillTarget)
        },
        "problems": {p.id: row(p) for p in session.query(Problem)},
        "problem_skills": {
            (p.problem_id, skill_key[p.skill_id]): p.mapping_weight_bp for p in session.query(ProblemSkill)
        },
        "mission_templates": {t.template_key: row(t) for t in session.query(MissionTemplate)},
        "roadmap_milestones": {m.milestone_key: row(m) for m in session.query(RoadmapMilestone)},
        "roadmap_milestone_skills": {
            skill_key[r.skill_id]: (milestone_key[r.milestone_id], r.position)
            for r in session.query(RoadmapMilestoneSkill)
        },
        "baseline_items": {b.item_key: row(b) for b in session.query(BaselineItem)},
        "catalog_loads": [
            (c.seed_version, c.catalog_fingerprint)
            for c in session.query(CatalogLoad).order_by(CatalogLoad.id)
        ],
    }
