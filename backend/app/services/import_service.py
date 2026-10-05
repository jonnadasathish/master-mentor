"""Import of a JSON export (format v2) into a database without preparation data: preview, validate, commit.

Surrogate ids of catalog rows (skills, role profiles) are remapped through the export's ``id_maps`` by
natural key. The commit is one transaction, needs an explicit confirmation, appends an IMPORT audit event
and finishes with a deterministic rebuild of every derived table. Existing history is never overwritten.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import Boolean, Date, DateTime, Numeric, Table, delete, func, insert, select
from sqlalchemy.orm import Session

from app.domain.activity.vocabulary import PERSONAL_PROBLEM_ID_START, PERSONAL_SEED_VERSION
from app.domain.clock import Clock
from app.errors import AppError
from app.models import AppSettings, AuditLog, Base, StartingProfile
from app.repositories.system_repository import SystemRepository
from app.schemas.envelope import ErrorCode
from app.services.export_service import DECISION_TABLES, DERIVED_TABLES, EXPORT_FORMAT, USER_TABLES
from app.services.mentor_service import MentorService

CONFIRMATION: Final = "IMPORT-INTO-EMPTY-DATABASE"
SUPPORTED_FORMAT_VERSION: Final = 2
IMPORT_ORDER: Final = (
    "goals",
    "mentor_runs",
    "problems",
    "problem_skills",
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
    "daily_plans",
    "plan_items",
    "weekly_reviews",
    "audit_log",
)
SKIPPED: Final = (
    "app_settings",
    "starting_profile",
    "catalog_loads",
)  # settings and the starting profile are applied separately; catalog comes from seed/
SKILL_FK: Final = {
    "problem_skills",
    "assessment_skills",
    "mock_round_skills",
    "story_competencies",
    "assessment_prompts",
    "plan_items",
}
# Goals are configuration (kept by dev-reset); an export that carries goals replaces them.
CONFIGURATION_TABLES: Final = ("app_settings", "starting_profile", "goals")
PREPARATION_TABLES: Final = tuple(
    t for t in (*USER_TABLES, *DECISION_TABLES) if t not in CONFIGURATION_TABLES
)


class ImportService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock

    def _table(self, name: str) -> Table:
        return Base.metadata.tables[name]

    def _count(self, name: str) -> int:
        return int(self._s.scalar(select(func.count()).select_from(self._table(name))) or 0)

    def _target_maps(self) -> tuple[dict[str, int], dict[str, int]]:
        skills = self._table("skills")
        profiles = self._table("role_profiles")
        return (
            {r.skill_key: r.id for r in self._s.execute(select(skills.c.id, skills.c.skill_key))},
            {r.profile_key: r.id for r in self._s.execute(select(profiles.c.id, profiles.c.profile_key))},
        )

    # ------------------------------------------------------------------ preview / validate
    def preview(self, doc: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        if doc.get("format") != EXPORT_FORMAT:
            errors.append(f"not a {EXPORT_FORMAT} document")
        if doc.get("format_version") != SUPPORTED_FORMAT_VERSION:
            version = doc.get("format_version")
            errors.append(f"format_version {version!r} is not supported (need {SUPPORTED_FORMAT_VERSION})")
        loaded = SystemRepository(self._s).loaded_seed_version()
        if doc.get("seed_version") != loaded:
            errors.append(
                f"export catalog {doc.get('seed_version')!r} differs from the loaded catalog {loaded!r}"
            )
        tables = doc.get("tables")
        maps = doc.get("id_maps") or {}
        if not isinstance(tables, dict):
            errors.append("tables missing")
            tables = {}
        target_skills, target_profiles = self._target_maps()
        skill_map: dict[str, Any] = maps.get("skills", {}) if isinstance(maps, dict) else {}
        profile_map: dict[str, Any] = maps.get("role_profiles", {}) if isinstance(maps, dict) else {}
        counts: dict[str, int] = {}
        for name, rows in tables.items():
            if name in SKIPPED:
                continue
            if name not in IMPORT_ORDER:
                errors.append(f"unknown table {name!r}")
                continue
            if not isinstance(rows, list):
                errors.append(f"{name}: rows must be a list")
                continue
            columns = {c.name for c in self._table(name).columns}
            counts[name] = len(rows)
            for n, row in enumerate(rows):
                if not isinstance(row, dict):
                    errors.append(f"{name}[{n}]: not an object")
                    break
                extra = set(row) - columns
                if extra:
                    errors.append(f"{name}[{n}]: unknown columns {sorted(extra)}")
                    break
                if name in SKILL_FK and row.get("skill_id") is not None:
                    key = skill_map.get(str(row["skill_id"]))
                    if key is None or key not in target_skills:
                        errors.append(
                            f"{name}[{n}]: skill id {row['skill_id']} has no matching skill in this catalog"
                        )
                        break
                if (
                    name == "goals"
                    and profile_map.get(str(row.get("role_profile_id"))) not in target_profiles
                ):
                    errors.append(f"goals[{n}]: role profile is not loaded in this catalog")
                    break
                if name == "problems" and (
                    row.get("seed_version") != PERSONAL_SEED_VERSION
                    or int(row.get("id", 0)) < PERSONAL_PROBLEM_ID_START
                ):
                    errors.append(f"problems[{n}]: only personal problems can be imported")
                    break
        occupied = {t: c for t in PREPARATION_TABLES if (c := self._count(t))}
        if occupied:
            errors.append(
                f"this database already has preparation data: {occupied}; import only into an empty one"
            )
        if not counts.get("problem_attempts") and not counts.get("assessments") and not counts.get("mocks"):
            warnings.append("the export contains no observations")
        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "counts": dict(sorted(counts.items())),
            "export_seed_version": doc.get("seed_version"),
            "loaded_seed_version": loaded,
            "exported_at": doc.get("exported_at"),
            "confirmation": CONFIRMATION,
        }

    # ------------------------------------------------------------------ commit
    def _convert(
        self,
        table: Table,
        row: dict[str, Any],
        skill_ids: dict[str, int],
        profile_ids: dict[str, int],
        skill_map: dict[str, str],
        profile_map: dict[str, str],
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for col in table.columns:
            if col.name not in row:
                continue
            value = row[col.name]
            if value is not None:
                if isinstance(col.type, DateTime):
                    value = (
                        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                        .astimezone(UTC)
                        .replace(tzinfo=None)
                    )
                elif isinstance(col.type, Date):
                    value = date.fromisoformat(str(value))
                elif isinstance(col.type, Numeric):
                    value = Decimal(str(value))
                elif isinstance(col.type, Boolean):
                    value = bool(value)
            out[col.name] = value
        if "skill_id" in out and out["skill_id"] is not None and table.name in SKILL_FK:
            out["skill_id"] = skill_ids[skill_map[str(out["skill_id"])]]
        if table.name == "goals":
            out["role_profile_id"] = profile_ids[profile_map[str(out["role_profile_id"])]]
        if table.name == "audit_log":
            out.pop("id", None)  # appended after the target's own audit rows
        return out

    def commit(self, doc: dict[str, Any], confirm: str) -> dict[str, Any]:
        if confirm != CONFIRMATION:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"Type {CONFIRMATION} to confirm the import.", 422)
        report = self.preview(doc)
        if not report["ok"]:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "The export cannot be imported.",
                422,
                {"errors": report["errors"]},
            )
        skill_ids, profile_ids = self._target_maps()
        maps = doc["id_maps"]
        tables = doc["tables"]
        # Derived tables and run rows of this (empty) database are replaced by a rebuild after the import.
        for name in (*DERIVED_TABLES, "mentor_runs"):
            self._s.execute(delete(self._table(name)))
        if tables.get("goals"):
            self._s.execute(delete(self._table("goals")))
        settings = tables.get("app_settings") or []
        row = self._s.get(AppSettings, 1)
        if settings and row is not None:
            row.timezone = settings[0].get("timezone", row.timezone)
            row.display_name = settings[0].get("display_name", row.display_name)
        profile_rows = tables.get("starting_profile") or []
        profile = self._s.get(StartingProfile, 1)
        if profile_rows and profile is not None:
            src = profile_rows[0]
            for field in ("experience_years", "current_role", "previous_role", "company_profile"):
                setattr(profile, field, src.get(field))
            profile.technologies_json = list(src.get("technologies_json") or [])
            profile.self_report_json = dict(src.get("self_report_json") or profile.self_report_json)
            for field in ("onboarding_completed_at", "updated_at"):
                value = src.get(field)
                if value is not None:
                    setattr(profile, field, datetime.fromisoformat(str(value)).replace(tzinfo=None))
        inserted: dict[str, int] = {}
        for name in IMPORT_ORDER:
            rows = tables.get(name) or []
            if not rows:
                continue
            table = self._table(name)
            values = [
                self._convert(table, r, skill_ids, profile_ids, maps["skills"], maps["role_profiles"])
                for r in rows
            ]
            self._s.execute(insert(table), values)
            inserted[name] = len(values)
        now = self._clock.now_utc().astimezone(UTC).replace(tzinfo=None)
        self._s.add(
            AuditLog(
                at=now,
                entity_type="system",
                entity_id="import",
                action="IMPORT",
                payload_json={"inserted": inserted, "exported_at": doc.get("exported_at")},
            )
        )
        self._s.commit()
        rebuild = MentorService(self._s, self._clock).rebuild()
        return {"inserted": inserted, "rebuild": rebuild}
