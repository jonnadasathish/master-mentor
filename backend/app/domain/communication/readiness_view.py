"""Communication Readiness (D-087): a read-only view derived from communication skill states.

An intentional V1 boundary: it is NOT a readiness component, has no weight, no gate and no overall number,
and never feeds Overall Readiness. It states what the system knows: measured browser-transcript rows, manual
self-review rows, and a self-reported-only declaration are kept apart.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

DEVELOPING_BELOW: Final = 50  # the T4 target score: below it the area is still developing
STRONG_FROM: Final = 70


@dataclass(frozen=True)
class AreaSpec:
    key: str
    title: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class SkillFact:
    score: int | None  # effective score from the existing skill state (None = unassessed)
    measured_rows: int  # speaking practices recorded from a browser transcript
    manual_rows: int  # speaking practices recorded by manual self-review
    other_rows: int  # any other evidence rows on the skill (checks, written practice)
    self_reported: bool  # a self-assessment exists (context only)


@dataclass(frozen=True)
class AreaView:
    key: str
    title: str
    status: str  # NOT_STARTED | DEVELOPING | WORKING | STRONG
    skills_total: int
    skills_with_evidence: int
    measured_rows: int
    manual_rows: int
    other_rows: int
    self_reported_only: int  # skills with a self-assessment and no evidence row at all


def area_status(scores: Sequence[int]) -> str:
    if not scores:
        return "NOT_STARTED"
    mean = sum(scores) // len(scores)
    if mean >= STRONG_FROM:
        return "STRONG"
    return "WORKING" if mean >= DEVELOPING_BELOW else "DEVELOPING"


def build_readiness_view(areas: Sequence[AreaSpec], facts: Mapping[str, SkillFact]) -> tuple[AreaView, ...]:
    out: list[AreaView] = []
    for area in areas:
        rows = [(s, facts[s]) for s in area.skills if s in facts]
        scored = [f.score for _, f in rows if f.score is not None]
        with_evidence = [f for _, f in rows if f.measured_rows + f.manual_rows + f.other_rows > 0]
        out.append(
            AreaView(
                key=area.key,
                title=area.title,
                status=area_status(scored),
                skills_total=len(area.skills),
                skills_with_evidence=len(with_evidence),
                measured_rows=sum(f.measured_rows for _, f in rows),
                manual_rows=sum(f.manual_rows for _, f in rows),
                other_rows=sum(f.other_rows for _, f in rows),
                self_reported_only=sum(
                    1
                    for _, f in rows
                    if f.self_reported and f.measured_rows + f.manual_rows + f.other_rows == 0
                ),
            )
        )
    return tuple(out)


STATUS_LABEL: Final = {
    "NOT_STARTED": "Not started",
    "DEVELOPING": "Developing",
    "WORKING": "Working",
    "STRONG": "Strong",
}


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def describe_area(view: AreaView) -> str:
    """One honest sentence about what the status rests on. It never turns self-report into evidence."""
    evidence = view.measured_rows + view.manual_rows + view.other_rows
    if evidence == 0:
        return "Self-reported only, not measured yet." if view.self_reported_only else "Not measured yet."
    parts = []
    if view.measured_rows:
        parts.append(_plural(view.measured_rows, "measured speaking practice"))
    if view.manual_rows:
        parts.append(_plural(view.manual_rows, "manual self-review"))
    if view.other_rows:
        parts.append(_plural(view.other_rows, "other practice or check record"))
    basis = " and ".join([", ".join(parts[:-1]), parts[-1]] if len(parts) > 1 else parts)
    if view.status == "NOT_STARTED":
        return f"Started: {basis}, but nothing scored yet."
    return f"{STATUS_LABEL[view.status]}: based on {basis}."
