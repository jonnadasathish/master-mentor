"""Full export of the user's preparation data (JSON document, or a zip of one CSV per table).

Every table is explicitly classified. ``USER`` and ``SYSTEM`` tables are exported in full; ``CATALOG``
tables are reproducible from ``seed/`` (only personal problems and their mappings are exported);
``DERIVED`` tables are rebuildable (POST /admin/rebuild) and are not exported.
A test fails when a new table is not classified.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.domain.activity.vocabulary import PERSONAL_SEED_VERSION
from app.domain.clock import Clock
from app.models import Base
from app.repositories.system_repository import SystemRepository

EXPORT_FORMAT: Final = "master-mentor-export"
EXPORT_FORMAT_VERSION: Final = 2  # v2 adds id_maps (surrogate id -> natural key) for import (D-075)

USER_TABLES: Final = (
    "app_settings",
    "starting_profile",
    "goals",
    "problem_attempts",
    "attempt_mistakes",
    "assessments",
    "assessment_skills",
    "revision_item_actions",
    "mocks",
    "mock_rounds",
    "mock_round_skills",
    "behavioral_stories",
    "story_competencies",
    "projects",
    "assessment_prompts",
)
SYSTEM_TABLES: Final = ("audit_log", "catalog_loads", "mentor_runs")
DECISION_TABLES: Final = ("daily_plans", "plan_items", "weekly_reviews")  # history: exported, never rebuilt
CATALOG_TABLES: Final = (
    "skill_groups",
    "skills",
    "skill_prerequisites",
    "role_profiles",
    "role_skill_targets",
    "problems",
    "problem_skills",
    "mission_templates",
    "roadmap_milestones",
    "roadmap_milestone_skills",
    "baseline_items",
)
DERIVED_TABLES: Final = (
    "evidence",
    "skill_states",
    "skill_daily_snapshots",
    "gap_states",
    "revision_items",
    "readiness_snapshots",
)
PERSONAL_CATALOG_TABLES: Final = (
    "problems",
    "problem_skills",
)  # rows owned by the user inside catalog tables


def classified_tables() -> set[str]:
    return (
        set(USER_TABLES)
        | set(SYSTEM_TABLES)
        | set(DECISION_TABLES)
        | set(CATALOG_TABLES)
        | set(DERIVED_TABLES)
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return aware.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


class ExportService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock

    def _table(self, name: str) -> Table:
        return Base.metadata.tables[name]

    def _rows(self, name: str) -> list[dict[str, Any]]:
        table = self._table(name)
        stmt = select(table).order_by(*table.primary_key.columns)
        if name == "problems":
            stmt = stmt.where(table.c.seed_version == PERSONAL_SEED_VERSION)
        if name == "problem_skills":
            problems = self._table("problems")
            stmt = stmt.where(
                table.c.problem_id.in_(
                    select(problems.c.id).where(problems.c.seed_version == PERSONAL_SEED_VERSION)
                )
            )
        return [{k: _json_value(v) for k, v in row.items()} for row in self._s.execute(stmt).mappings()]

    def exported_table_names(self) -> list[str]:
        return [*USER_TABLES, *PERSONAL_CATALOG_TABLES, *DECISION_TABLES, *SYSTEM_TABLES]

    def id_maps(self) -> dict[str, dict[str, str]]:
        """Surrogate ids that exported rows reference, mapped to natural keys (stable across installs)."""
        skills = self._table("skills")
        profiles = self._table("role_profiles")
        return {
            "skills": {
                str(r.id): r.skill_key for r in self._s.execute(select(skills.c.id, skills.c.skill_key))
            },
            "role_profiles": {
                str(r.id): r.profile_key
                for r in self._s.execute(select(profiles.c.id, profiles.c.profile_key))
            },
        }

    def document(self) -> dict[str, Any]:
        tables = {name: self._rows(name) for name in self.exported_table_names()}
        return {
            "id_maps": self.id_maps(),
            "format": EXPORT_FORMAT,
            "format_version": EXPORT_FORMAT_VERSION,
            "exported_at": _json_value(self._clock.now_utc()),
            "seed_version": SystemRepository(self._s).loaded_seed_version(),
            "counts": {name: len(rows) for name, rows in tables.items()},
            "tables": tables,
        }

    def json_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")

    def csv_zip_bytes(self) -> bytes:
        doc = self.document()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            manifest = {k: v for k, v in doc.items() if k != "tables"}
            archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=1))
            for name in self.exported_table_names():
                columns = [c.name for c in self._table(name).columns]
                text = io.StringIO()
                writer = csv.DictWriter(text, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                for row in doc["tables"][name]:
                    writer.writerow(
                        {
                            k: json.dumps(v, sort_keys=True) if isinstance(v, dict | list) else v
                            for k, v in row.items()
                        }
                    )
                archive.writestr(f"{name}.csv", text.getvalue())
        return buffer.getvalue()

    def filename_stamp(self) -> str:
        return self._clock.now_utc().strftime("%Y%m%dT%H%M%SZ")
