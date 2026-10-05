"""Seed validation and deterministic, idempotent catalog loading.

Flow: read files → validate (pure) → abort with diagnostics before any write → in ONE transaction upsert every
catalog table by natural key → record a ``catalog_loads`` row and an audit event only if something changed.
Running it repeatedly with the same seed leaves the database byte-for-byte equivalent (no new rows).
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.activity.vocabulary import PERSONAL_SEED_VERSION
from app.domain.catalog.issues import Issue
from app.domain.catalog.model import Catalog
from app.domain.catalog.validate import ValidationResult, validate_seed
from app.domain.clock import Clock
from app.infrastructure.seed_files import append_lock_entry, read_seed
from app.models import (
    AuditLog,
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


class SeedValidationError(Exception):
    def __init__(self, issues: tuple[Issue, ...]):
        super().__init__(f"seed validation failed with {len(issues)} error(s)")
        self.issues = issues


@dataclass
class TableCounts:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    deleted: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.inserted or self.updated or self.deactivated or self.deleted)


@dataclass
class LoadReport:
    seed_version: str
    catalog_fingerprint: str
    file_fingerprints: Mapping[str, str]
    tables: dict[str, TableCounts] = field(default_factory=dict)
    catalog_load_id: int | None = None

    @property
    def changed(self) -> bool:
        return any(c.changed for c in self.tables.values())


def validate_seed_dir(seed_dir: str | Path) -> ValidationResult:
    raw, lock = read_seed(seed_dir)
    return validate_seed(raw, lock)


def lock_seed_dir(seed_dir: str | Path) -> tuple[str, Path]:
    """Freeze fingerprints for the current (new) seed_version. Content must otherwise be valid."""
    raw, lock = read_seed(seed_dir)
    result = validate_seed(raw, lock)
    blocking = [i for i in result.errors if i.code != "lock.unlocked_version"]
    if blocking:
        raise SeedValidationError(tuple(blocking))
    if not any(i.code == "lock.unlocked_version" for i in result.errors):
        raise SeedValidationError(
            (
                Issue(
                    "lock.already_locked",
                    "seed.lock.yaml",
                    "this seed_version is already locked; nothing to do",
                ),
            )
        )
    seed_version = str(next(iter(raw.values()))["seed_version"])  # validated: identical in every file
    path = append_lock_entry(seed_dir, seed_version, result.file_fingerprints, result.catalog_fingerprint)
    return seed_version, path


class SeedLoader:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def load(self, seed_dir: str | Path) -> LoadReport:
        result = validate_seed_dir(seed_dir)
        if not result.ok or result.catalog is None:
            raise SeedValidationError(result.errors)  # nothing has been written
        conflicts = self._personal_problem_conflicts(result.catalog)
        if conflicts:
            raise SeedValidationError(conflicts)  # nothing has been written
        report = LoadReport(
            result.catalog.seed_version, result.catalog_fingerprint, dict(result.file_fingerprints)
        )
        try:
            self._apply(result.catalog, report)
            if report.changed or self._session.scalar(select(CatalogLoad.id).limit(1)) is None:
                self._record(report)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return report

    def _personal_problem_conflicts(self, catalog: Catalog) -> tuple[Issue, ...]:
        """A seed problem must never take over a personal problem's identity (platform, platform_key)."""
        wanted = {(p.platform, p.platform_key): p.id for p in catalog.problems}
        personal = self._session.scalars(select(Problem).where(Problem.seed_version == PERSONAL_SEED_VERSION))
        return tuple(
            Issue(
                "problems.conflicts_with_personal",
                f"problems.yaml: problems[id={wanted[(row.platform, row.platform_key)]}]",
                f"{row.platform}:{row.platform_key} already exists as personal problem {row.id}; rename the "
                "seed problem or remove the clash first",
            )
            for row in personal
            if (row.platform, row.platform_key) in wanted
        )

    # ------------------------------------------------------------------------------------------- apply

    def _apply(self, catalog: Catalog, report: LoadReport) -> None:
        sv = catalog.seed_version
        s = self._session

        groups = _sync(
            s,
            SkillGroup,
            key=lambda r: r.group_key,
            desired=[
                {
                    "group_key": g.key,
                    "name": g.name,
                    "component": g.component,
                    "position": i,
                    "seed_version": sv,
                }
                for i, g in enumerate(catalog.groups, start=1)
            ],
            desired_key=lambda d: d["group_key"],
            on_missing="keep",  # deactivated skills may still reference a removed group
            counts=report.tables.setdefault("skill_groups", TableCounts()),
            flush=True,
        )
        group_id = {k: row.id for k, row in groups.items()}

        skills = _sync(
            s,
            Skill,
            key=lambda r: r.skill_key,
            desired=[
                {
                    "skill_key": sk.key,
                    "name": sk.name,
                    "group_id": group_id[sk.parent],
                    "component": sk.component,
                    "is_pattern": sk.is_pattern,
                    "evidence_kinds": list(sk.evidence_kinds),
                    "topics": list(sk.topics),
                    "position": i,
                    "active": True,
                    "seed_version": sv,
                }
                for i, sk in enumerate(catalog.skills, start=1)
            ],
            desired_key=lambda d: d["skill_key"],
            on_missing="deactivate",
            counts=report.tables.setdefault("skills", TableCounts()),
            flush=True,
        )
        skill_id = {k: row.id for k, row in skills.items()}

        _sync(
            s,
            SkillPrerequisite,
            key=lambda r: (r.skill_id, r.prereq_skill_id),
            desired=[
                {
                    "skill_id": skill_id[sk.key],
                    "prereq_skill_id": skill_id[p.skill],
                    "min_score": p.min_score,
                    "position": j,
                }
                for sk in catalog.skills
                for j, p in enumerate(sk.prerequisites, start=1)
            ],
            desired_key=lambda d: (d["skill_id"], d["prereq_skill_id"]),
            on_missing="delete",
            counts=report.tables.setdefault("skill_prerequisites", TableCounts()),
        )

        profiles = _sync(
            s,
            RoleProfile,
            key=lambda r: r.profile_key,
            desired=[
                {
                    "profile_key": p.profile_key,
                    "name": p.name,
                    "seniority": p.seniority,
                    "config_json": _plain(p.config),
                    "seed_version": sv,
                }
                for p in catalog.profiles
            ],
            desired_key=lambda d: d["profile_key"],
            on_missing="delete",
            counts=report.tables.setdefault("role_profiles", TableCounts()),
            flush=True,
            delete_children=lambda ids: s.query(RoleSkillTarget).filter(RoleSkillTarget.profile_id.in_(ids)),
        )
        _sync(
            s,
            RoleSkillTarget,
            key=lambda r: (r.profile_id, r.skill_id),
            desired=[
                {
                    "profile_id": profiles[p.profile_key].id,
                    "skill_id": skill_id[t.skill],
                    "tier": t.tier,
                    "importance": t.importance,
                    "target_score": t.target_score,
                    "floor_score": t.floor_score,
                }
                for p in catalog.profiles
                for t in p.targets
            ],
            desired_key=lambda d: (d["profile_id"], d["skill_id"]),
            on_missing="delete",
            counts=report.tables.setdefault("role_skill_targets", TableCounts()),
        )

        _sync(
            s,
            Problem,
            key=lambda r: r.id,
            desired=[
                {
                    "id": p.id,
                    "platform": p.platform,
                    "platform_key": p.platform_key,
                    "title": p.title,
                    "url": None,
                    "difficulty": p.difficulty,
                    "expected_minutes": p.expected_minutes,
                    "is_canonical": p.is_canonical,
                    "active": True,
                    "seed_version": sv,
                }
                for p in catalog.problems
            ],
            desired_key=lambda d: d["id"],
            on_missing="deactivate",
            counts=report.tables.setdefault("problems", TableCounts()),
            scope=lambda q: q.filter(
                Problem.seed_version != PERSONAL_SEED_VERSION
            ),  # user problems are never touched
            flush=True,
        )
        _sync(
            s,
            ProblemSkill,
            key=lambda r: (r.problem_id, r.skill_id),
            desired=[
                {"problem_id": p.id, "skill_id": skill_id[m.skill], "mapping_weight_bp": m.mapping_weight_bp}
                for p in catalog.problems
                for m in p.skills
            ],
            desired_key=lambda d: (d["problem_id"], d["skill_id"]),
            on_missing="delete",
            counts=report.tables.setdefault("problem_skills", TableCounts()),
            scope=lambda q: q.filter(
                ProblemSkill.problem_id.in_(
                    select(Problem.id).where(Problem.seed_version != PERSONAL_SEED_VERSION)
                )
            ),
        )

        _sync(
            s,
            MissionTemplate,
            key=lambda r: r.template_key,
            desired=[
                {
                    "template_key": t.key,
                    "component": t.component,
                    "stages": list(t.stages),
                    "gap_types": _list_or_none(t.gap_types),
                    "applies_to": _list_or_none(t.applies_to),
                    "item_type": t.item_type,
                    "minutes": t.minutes,
                    "minutes_rule": t.minutes_rule,
                    "min_budget": t.min_budget,
                    "difficulty": t.difficulty,
                    "needs_problem": t.needs_problem,
                    "observation_json": _plain(t.observation),
                    "pass_rule": t.pass_rule,
                    "partial_rule": t.partial_rule,
                    "output_level": t.output_level,
                    "next_on_pass": t.next_on_pass,
                    "next_on_fail": t.next_on_fail,
                    "position": i,
                    "seed_version": sv,
                }
                for i, t in enumerate(catalog.templates, start=1)
            ],
            desired_key=lambda d: d["template_key"],
            on_missing="delete",
            counts=report.tables.setdefault("mission_templates", TableCounts()),
        )

        milestones = _sync(
            s,
            RoadmapMilestone,
            key=lambda r: r.milestone_key,
            desired=[
                {
                    "milestone_key": m.key,
                    "track": m.track,
                    "track_position": m.track_position,
                    "position": m.position,
                    "name": m.name,
                    "extra_exit_json": list(m.extra_exit),
                    "content": m.content,
                    "starts_when": m.starts_when,
                    "seed_version": sv,
                }
                for m in catalog.milestones
            ],
            desired_key=lambda d: d["milestone_key"],
            on_missing="delete",
            counts=report.tables.setdefault("roadmap_milestones", TableCounts()),
            flush=True,
            delete_children=lambda ids: s.query(RoadmapMilestoneSkill).filter(
                RoadmapMilestoneSkill.milestone_id.in_(ids)
            ),
        )
        _sync(
            s,
            RoadmapMilestoneSkill,
            key=lambda r: r.skill_id,
            desired=[
                {"skill_id": skill_id[k], "milestone_id": milestones[m.key].id, "position": j}
                for m in catalog.milestones
                for j, k in enumerate(m.skills, start=1)
            ],
            desired_key=lambda d: d["skill_id"],
            on_missing="delete",
            counts=report.tables.setdefault("roadmap_milestone_skills", TableCounts()),
        )
        _sync(
            s,
            BaselineItem,
            key=lambda r: r.item_key,
            desired=[
                {
                    "item_key": b.key,
                    "position": b.position,
                    "name": b.name,
                    "minutes": b.minutes,
                    "observation_kind": b.observation_kind,
                    "covers_json": list(b.covers),
                    "seed_version": sv,
                }
                for b in catalog.baseline
            ],
            desired_key=lambda d: d["item_key"],
            on_missing="delete",
            counts=report.tables.setdefault("baseline_items", TableCounts()),
        )
        s.flush()

    def _record(self, report: LoadReport) -> None:
        now = self._clock.now_utc()
        counts = {name: vars(c) for name, c in sorted(report.tables.items())}
        load = CatalogLoad(
            seed_version=report.seed_version,
            catalog_fingerprint=report.catalog_fingerprint,
            file_fingerprints_json=dict(report.file_fingerprints),
            counts_json=counts,
            loaded_at=now.replace(tzinfo=None),
        )
        self._session.add(load)
        self._session.flush()
        report.catalog_load_id = load.id
        self._session.add(
            AuditLog(
                at=now.replace(tzinfo=None),
                entity_type="catalog",
                entity_id=report.seed_version,
                action="seed_loaded",
                payload_json={
                    "catalog_load_id": load.id,
                    "catalog_fingerprint": report.catalog_fingerprint,
                    "counts": counts,
                },
            )
        )


def _sync(
    session: Session,
    model: type[Any],
    *,
    key: Callable[[Any], Hashable],
    desired: Iterable[dict[str, Any]],
    desired_key: Callable[[dict[str, Any]], Hashable],
    on_missing: str,
    counts: TableCounts,
    scope: Callable[[Any], Any] | None = None,
    flush: bool = False,
    delete_children: Callable[[list[Any]], Any] | None = None,
) -> dict[Hashable, Any]:
    """Upsert ``desired`` rows by natural key. Rows no longer desired are kept, deactivated, or deleted
    (``on_missing``). Returns the desired rows by natural key."""
    query = session.query(model)
    if scope is not None:
        query = scope(query)
    existing = {key(row): row for row in query.all()}
    result: dict[Hashable, Any] = {}
    for values in desired:
        k = desired_key(values)
        row = existing.pop(k, None)
        if row is None:
            row = model(**values)
            session.add(row)
            counts.inserted += 1
        else:
            changed = False
            for column, value in values.items():
                if getattr(row, column) != value:
                    setattr(row, column, value)
                    changed = True
            counts.updated += changed
            counts.unchanged += not changed
        result[k] = row
    leftovers = [existing[k] for k in sorted(existing, key=repr)]  # deterministic processing order
    if on_missing == "keep":
        counts.unchanged += len(leftovers)
    elif on_missing == "deactivate":
        for row in leftovers:
            if row.active:
                row.active = False
                counts.deactivated += 1
            else:
                counts.unchanged += 1
    else:
        if delete_children is not None and leftovers:
            delete_children([row.id for row in leftovers]).delete(synchronize_session=False)
        for row in leftovers:
            session.delete(row)
            counts.deleted += 1
    if flush:
        session.flush()
    return result


def _plain(value: Any) -> Any:
    """Mappings/tuples from the frozen domain model -> plain JSON-compatible dict/list for JSON columns."""
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def _list_or_none(value: tuple[str, ...] | None) -> list[str] | None:
    return list(value) if value is not None else None
