"""Catalog seed commands.

    python -m app.cli.catalog validate   # validate seed/*.yaml (no database access); exit 1 on errors
    python -m app.cli.catalog seed       # validate, then load idempotently into the database
    python -m app.cli.catalog lock       # freeze fingerprints for a NEW seed_version (append-only)
    python -m app.cli.catalog status     # which catalog version is loaded

Exit codes: 0 success, 1 validation errors, 2 operational error (unreadable file, database).
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.infrastructure.clock import SystemClock
from app.infrastructure.db import session_factory
from app.infrastructure.seed_files import SeedFileError
from app.repositories.catalog_repository import CatalogRepository
from app.services.seed_service import SeedLoader, SeedValidationError, lock_seed_dir, validate_seed_dir


def _print_issues(issues: object) -> None:
    for issue in issues:  # type: ignore[attr-defined]
        print(issue.render(), file=sys.stderr)
        print(file=sys.stderr)


def cmd_validate(seed_dir: str) -> int:
    result = validate_seed_dir(seed_dir)
    if result.errors:
        _print_issues(result.errors)
        print(f"Seed INVALID: {len(result.errors)} error(s) in {seed_dir}", file=sys.stderr)
        return 1
    catalog = result.catalog
    assert catalog is not None
    print(f"Seed valid: {catalog.seed_version} (catalog fingerprint {result.catalog_fingerprint[:12]})")
    print(
        f"  groups={len(catalog.groups)} skills={len(catalog.skills)} "
        f"prerequisites={sum(len(s.prerequisites) for s in catalog.skills)} "
        f"profiles={len(catalog.profiles)} role_targets={sum(len(p.targets) for p in catalog.profiles)} "
        f"problems={len(catalog.problems)} problem_skills={sum(len(p.skills) for p in catalog.problems)} "
        f"milestones={len(catalog.milestones)} baseline_items={len(catalog.baseline)} "
        f"templates={len(catalog.templates)} max_prerequisite_depth={catalog.max_depth}"
    )
    for role, fingerprint in result.file_fingerprints.items():
        print(f"  {role:<44} {fingerprint[:16]}")
    return 0


def cmd_seed(seed_dir: str) -> int:
    session = session_factory()()
    try:
        report = SeedLoader(session, SystemClock()).load(seed_dir)
    except SeedValidationError as exc:
        _print_issues(exc.issues)
        print("Seed INVALID: nothing was written to the database.", file=sys.stderr)
        return 1
    finally:
        session.close()
    state = "changed" if report.changed else "unchanged (idempotent no-op)"
    print(
        f"Seed {report.seed_version} loaded: {state}; catalog fingerprint {report.catalog_fingerprint[:12]}"
    )
    print(f"  {'table':<26}{'inserted':>9}{'updated':>9}{'unchanged':>10}{'deactivated':>12}{'deleted':>8}")
    for name, c in report.tables.items():
        print(f"  {name:<26}{c.inserted:>9}{c.updated:>9}{c.unchanged:>10}{c.deactivated:>12}{c.deleted:>8}")
    if report.catalog_load_id is not None:
        print(f"  recorded catalog_loads.id={report.catalog_load_id}")
    return 0


def cmd_lock(seed_dir: str) -> int:
    try:
        version, path = lock_seed_dir(seed_dir)
    except SeedValidationError as exc:
        _print_issues(exc.issues)
        return 1
    print(f"Locked {version} in {path}")
    return 0


def cmd_status() -> int:
    session = session_factory()()
    try:
        load = CatalogRepository(session).current_load()
    finally:
        session.close()
    if load is None:
        print("No catalog loaded. Run: make seed")
        return 1
    print(
        f"Loaded catalog: {load.seed_version} fingerprint {load.catalog_fingerprint} at {load.loaded_at} UTC"
    )
    for role, fingerprint in sorted(load.file_fingerprints_json.items()):
        print(f"  {role:<44} {fingerprint[:16]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli.catalog", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["validate", "seed", "lock", "status"])
    parser.add_argument("--seed-dir", default=None, help="defaults to SEED_DIR")
    args = parser.parse_args(argv)
    seed_dir = args.seed_dir or get_settings().seed_dir
    try:
        if args.command == "validate":
            return cmd_validate(seed_dir)
        if args.command == "seed":
            return cmd_seed(seed_dir)
        if args.command == "lock":
            return cmd_lock(seed_dir)
        return cmd_status()
    except SeedFileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except SQLAlchemyError as exc:
        print(f"ERROR: database operation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
