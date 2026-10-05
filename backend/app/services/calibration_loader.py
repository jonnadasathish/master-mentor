"""Loads the baseline battery + completed battery keys + required skills and evaluates Calibration Mode."""

from __future__ import annotations

from collections.abc import Collection
from types import ModuleType

from sqlalchemy.orm import Session

from app.domain.baseline.calibration import BatteryItem, CalibrationStatus, calibration_status
from app.domain.profile.model import SkillGraph
from app.repositories.activity_repository import ActivityRepository
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.plan_repository import PlanRepository


def load_calibration(
    session: Session, graph: SkillGraph, assessed_skills: Collection[str], ruleset: ModuleType
) -> CalibrationStatus:
    battery = [
        BatteryItem(b.item_key, b.position, b.name, b.minutes, b.observation_kind, tuple(b.covers_json))
        for b in CatalogRepository(session).baseline_items()
    ]
    completed = (
        ActivityRepository(session).battery_keys()
        | AssessmentRepository(session).battery_keys()
        | PlanRepository(session).done_battery_keys()  # a DONE plan item completes its battery item
    )
    required = [k for k, s in graph.skills.items() if s.required]
    return calibration_status(
        battery=battery,
        completed_keys=completed,
        required_skills=required,
        assessed_skills=assessed_skills,
        ruleset=ruleset,
    )
