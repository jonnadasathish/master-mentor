"""Validation diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    code: str  # dotted, e.g. "graph.cycle", "profile.unknown_skill"
    where: str  # file and path, e.g. "problems.yaml: problems[id=3].skills"
    message: str
    severity: str = "ERROR"  # ERROR | WARNING

    @property
    def is_error(self) -> bool:
        return self.severity == "ERROR"

    def render(self) -> str:
        return f"{self.severity}: {self.code}\n  at {self.where}\n  {self.message}"
