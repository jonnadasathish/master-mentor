"""CLI: ``python -m app.cli.export all --out /exports`` writes a JSON export and a CSV zip (make export)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.infrastructure.clock import SystemClock
from app.infrastructure.db import session_factory
from app.services.export_service import ExportService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli.export")
    parser.add_argument("what", choices=["all", "json", "csv"])
    parser.add_argument("--out", default="/exports")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with session_factory()() as session:
        export = ExportService(session, SystemClock())
        stamp = export.filename_stamp()
        if args.what in ("all", "json"):
            path = out / f"master-mentor-export-{stamp}.json"
            path.write_bytes(export.json_bytes())
            print(f"wrote {path}")
        if args.what in ("all", "csv"):
            path = out / f"master-mentor-export-{stamp}.zip"
            path.write_bytes(export.csv_zip_bytes())
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
