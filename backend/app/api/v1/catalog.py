"""Catalog read API (static seed data). Every response uses the standard envelope with meta.seed_version."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infrastructure.db import get_session
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.envelope import Meta, success
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_catalog(session: Annotated[Session, Depends(get_session)]) -> CatalogService:
    return CatalogService(CatalogRepository(session))


Catalog = Annotated[CatalogService, Depends(get_catalog)]


def _list(catalog: CatalogService, items: list[Any]) -> dict[str, Any]:
    return success(
        [i.model_dump(mode="json") for i in items],
        Meta(seed_version=catalog.seed_version(), count=len(items)),
    )


def _one(catalog: CatalogService, item: Any) -> dict[str, Any]:
    return success(item, Meta(seed_version=catalog.seed_version()))


@router.get("")
def summary(catalog: Catalog) -> dict[str, Any]:
    """Loaded catalog version, per-file fingerprints and row counts."""
    return _one(catalog, catalog.summary())


@router.get("/skills")
def list_skills(
    catalog: Catalog,
    component: str | None = None,
    group: str | None = None,
    tier: str | None = Query(default=None, pattern="^T[1-4]$"),
) -> dict[str, Any]:
    return _list(catalog, catalog.skills(component=component, group=group, tier=tier))


@router.get("/skills/{skill_key}")
def get_skill(catalog: Catalog, skill_key: str) -> dict[str, Any]:
    return _one(catalog, catalog.skill(skill_key))


@router.get("/skills/{skill_key}/prerequisites")
def get_prerequisites(catalog: Catalog, skill_key: str, transitive: bool = False) -> dict[str, Any]:
    return _one(catalog, catalog.prerequisites(skill_key, transitive=transitive))


@router.get("/skills/{skill_key}/dependents")
def get_dependents(catalog: Catalog, skill_key: str) -> dict[str, Any]:
    return _list(catalog, catalog.dependents(skill_key))


@router.get("/tree")
def skill_tree(catalog: Catalog) -> dict[str, Any]:
    """Components → skill groups → skill keys (seed order)."""
    return _list(catalog, catalog.tree())


@router.get("/groups/{group_key}/skills")
def group_skills(catalog: Catalog, group_key: str) -> dict[str, Any]:
    return _list(catalog, catalog.group_children(group_key))


@router.get("/role-profile")
def role_profile(catalog: Catalog, profile_key: str | None = None) -> dict[str, Any]:
    return _one(catalog, catalog.role_profile(profile_key))


@router.get("/role-profile/targets")
def role_targets(
    catalog: Catalog, profile_key: str | None = None, required: bool | None = None
) -> dict[str, Any]:
    return _list(catalog, catalog.targets(profile_key=profile_key, required=required))


@router.get("/roadmap")
def roadmap(catalog: Catalog) -> dict[str, Any]:
    return _one(catalog, catalog.roadmap())


@router.get("/roadmap/milestones/{milestone_key}")
def milestone(catalog: Catalog, milestone_key: str) -> dict[str, Any]:
    return _one(catalog, catalog.milestone(milestone_key))


@router.get("/problems")
def list_problems(
    catalog: Catalog, skill: str | None = None, difficulty: str | None = None
) -> dict[str, Any]:
    return _list(catalog, catalog.problems(skill=skill, difficulty=difficulty))


@router.get("/problems/by-key/{platform}/{platform_key}")
def problem_by_key(catalog: Catalog, platform: str, platform_key: str) -> dict[str, Any]:
    return _one(catalog, catalog.problem_by_key(platform, platform_key))


@router.get("/problems/{problem_id}")
def get_problem(catalog: Catalog, problem_id: int) -> dict[str, Any]:
    return _one(catalog, catalog.problem(problem_id))


@router.get("/mission-templates")
def list_templates(
    catalog: Catalog, component: str | None = None, stage: str | None = None, skill: str | None = None
) -> dict[str, Any]:
    return _list(catalog, catalog.templates(component=component, stage=stage, skill=skill))


@router.get("/mission-templates/resolve")
def resolve_template(
    catalog: Catalog, component: str, stage: str, skill: str, gap_type: str | None = None
) -> dict[str, Any]:
    """Which template the mentor would use (MISSION_LIBRARY.md §1); 404 CONTENT_MISSING if none."""
    return _one(catalog, catalog.resolve(component=component, stage=stage, skill=skill, gap_type=gap_type))
