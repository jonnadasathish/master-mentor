"""DEVELOPER-ONLY tools. Never run automatically; refuses outside APP_ENV=development.

``python -m app.cli.devtools reset-prep --confirm RESET-PREP-DATA`` (via ``make dev-reset CONFIRM=...``, which
takes a backup first) deletes every preparation record — attempts, assessments, personal problems, derived
tables, mentor runs — and keeps the catalog (seed data) and app_settings. The reset itself is audited.
"""

from __future__ import annotations

import argparse
import sys
from typing import Final

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.config import Environment, get_settings
from app.domain.activity.vocabulary import PERSONAL_SEED_VERSION
from app.infrastructure.clock import SystemClock
from app.infrastructure.db import session_factory
from app.models import AuditLog, Base, Problem, ProblemSkill
from app.services.export_service import DECISION_TABLES, DERIVED_TABLES, USER_TABLES

CONFIRMATION: Final = "RESET-PREP-DATA"
KEEP: Final = ("app_settings", "goals")  # configuration, not preparation data
# Children before parents. Later slices append their user tables to USER_TABLES / DERIVED_TABLES.
DELETE_ORDER_FIRST: Final = (*DERIVED_TABLES, *DECISION_TABLES, "mentor_runs")


def _count(result: object) -> int:
    return int(getattr(result, "rowcount", 0))


def reset_prep(session: Session) -> dict[str, int]:
    deleted: dict[str, int] = {}
    tables = Base.metadata.tables
    session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    try:
        for name in [*DELETE_ORDER_FIRST, *reversed([t for t in USER_TABLES if t not in KEEP])]:
            deleted[name] = _count(session.execute(delete(tables[name])))
        personal = select(Problem.id).where(Problem.seed_version == PERSONAL_SEED_VERSION)
        deleted["problem_skills(personal)"] = _count(
            session.execute(delete(ProblemSkill).where(ProblemSkill.problem_id.in_(personal)))
        )
        deleted["problems(personal)"] = _count(
            session.execute(delete(Problem).where(Problem.seed_version == PERSONAL_SEED_VERSION))
        )
    finally:
        session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    session.add(
        AuditLog(
            at=SystemClock().now_utc().replace(tzinfo=None),
            entity_type="system",
            entity_id="preparation-data",
            action="DEV_RESET",
            payload_json={"deleted": deleted},
        )
    )
    session.commit()
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli.devtools")
    sub = parser.add_subparsers(dest="command", required=True)
    reset = sub.add_parser("reset-prep", help="DEV ONLY: delete all preparation data, keep the catalog")
    reset.add_argument("--confirm", default="")
    args = parser.parse_args(argv)
    if get_settings().app_env != Environment.DEVELOPMENT:
        print("refused: reset-prep only runs with APP_ENV=development", file=sys.stderr)
        return 2
    if args.confirm != CONFIRMATION:
        print(
            f"refused: pass --confirm {CONFIRMATION} (make dev-reset CONFIRM={CONFIRMATION})", file=sys.stderr
        )
        return 2
    with session_factory()() as session:
        deleted = reset_prep(session)
        remaining = session.scalar(select(func.count()).select_from(Base.metadata.tables["skills"]))
    for name, count in deleted.items():
        print(f"deleted {count:>6} {name}")
    print(f"catalog kept: {remaining} skills. Next: open the app; the next read recalculates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
