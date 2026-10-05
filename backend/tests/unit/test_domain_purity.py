"""Hardening (CLAUDE.md rule 3): domain engines are pure — no clock, randomness, ids, environment or I/O."""

from __future__ import annotations

import ast
from pathlib import Path

DOMAIN = Path(__file__).resolve().parents[2] / "app" / "domain"
FORBIDDEN_MODULES = {
    "random",
    "secrets",
    "uuid",
    "time",
    "os",
    "socket",
    "requests",
    "httpx",
    "sqlalchemy",
    "pathlib",
}
FORBIDDEN_NAMES = {"open", "input", "print", "eval", "exec"}
FORBIDDEN_ATTRS = {("datetime", "now"), ("datetime", "utcnow"), ("datetime", "today"), ("date", "today")}
ALLOWED_IMPORTS = {"clock.py": {"zoneinfo"}}  # local_date converts an injected instant


def test_domain_modules_never_import_io_randomness_or_clock() -> None:
    offenders: list[str] = []
    for path in sorted(DOMAIN.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for name in names:
                    if name.split(".")[0] in FORBIDDEN_MODULES:
                        offenders.append(f"{path.relative_to(DOMAIN)} imports {name}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
                    offenders.append(f"{path.relative_to(DOMAIN)} calls {node.func.id}()")
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in FORBIDDEN_ATTRS
                ):
                    offenders.append(
                        f"{path.relative_to(DOMAIN)} calls {node.func.value.id}.{node.func.attr}()"
                    )
    assert offenders == []


def test_domain_never_uses_float_literals_in_math() -> None:
    offenders = [
        f"{path.relative_to(DOMAIN)}:{node.lineno}"
        for path in sorted(DOMAIN.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    assert offenders == []
