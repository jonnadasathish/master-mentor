"""Builds revision observations from engine inputs + derived evidence rows (pure)."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.evidence.model import AssessmentObservation, AttemptObservation, EvidenceRow
from app.domain.revision.model import ProblemFact, RevisionObservation, RowFact

PRIMARY_BP = 10000


def revision_observations(
    attempts: Sequence[AttemptObservation],
    assessments: Sequence[AssessmentObservation],
    rows: Sequence[EvidenceRow],
) -> list[RevisionObservation]:
    by_source: dict[tuple[str, int], list[RowFact]] = {}
    for r in rows:
        by_source.setdefault((r.source_type, r.source_id), []).append(
            RowFact(r.skill, r.level, r.outcome_points, r.is_scoring, r.time_ratio_bp)
        )
    out: list[RevisionObservation] = []
    for a in attempts:
        primary = next((skill for skill, bp in a.mappings if bp == PRIMARY_BP), None)
        out.append(
            RevisionObservation(
                source_type="ATTEMPT",
                source_id=a.id,
                observed_on=a.attempted_on,
                observed_at=a.attempted_at,
                rows=tuple(by_source.get(("ATTEMPT", a.id), ())),
                revision_item_key=a.revision_item_key,
                problem=ProblemFact(a.problem_id, a.difficulty, a.is_canonical, a.is_catalog, primary),
                outcome=a.outcome,
                hints_used=a.hints_used,
                solution_viewed=a.solution_viewed,
                time_seconds=a.time_seconds,
            )
        )
    for s in assessments:
        out.append(
            RevisionObservation(
                source_type="ASSESSMENT",
                source_id=s.id,
                observed_on=s.observed_on,
                observed_at=s.observed_at,
                rows=tuple(by_source.get(("ASSESSMENT", s.id), ())),
                revision_item_key=s.revision_item_key,
                kind=s.kind,
                source_key=s.source_key,
            )
        )
    return out
