"""Communication read models (D-087): Communication Readiness and the transcript preview.

Both are read-only and derived. Nothing here is an evidence rule: skill states come from the existing
engine and speaking metrics only rate the measurable criteria of a practice before it is submitted.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.domain.communication.metrics import (
    compute_speaking_metrics,
    rate_measured_criteria,
    speech_errors,
    targets_from_body,
)
from app.domain.communication.readiness_view import (
    STATUS_LABEL,
    AreaSpec,
    SkillFact,
    build_readiness_view,
    describe_area,
)
from app.errors import AppError
from app.models import StartingProfile
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.communication_repository import CommunicationRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.learning_repository import LearningRepository
from app.schemas.communication import (
    CommunicationAreaOut,
    CommunicationReadinessOut,
    CommunicationSkillOut,
    SpeakingHistoryOut,
    SpeakingHistoryRowOut,
    SpeechPreviewIn,
    SpeechPreviewOut,
)
from app.schemas.envelope import ErrorCode
from app.services.catalog_service import CatalogService
from app.services.learning_service import _speaking_out

TRACK_KEY = "communication"
CLAIM_WORDS = {
    "strengths": "strong",
    "weaknesses": "weak",
    "never_studied": "never studied",
    "recently_studied": "recently studied",
}
HISTORY_NOTE = (
    "Transcripts and counts only; Master Mentor never stores audio. Counts are signals from practice, "
    "not a grade of your English."
)
NOTE = (
    "Communication Readiness is a separate, read-only view. It is not part of Overall Readiness and does not "
    "change any readiness gate. Metrics are signals from practice, not a grade of your English."
)


class CommunicationService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._s = session
        self._clock = clock
        self._learning_repo = LearningRepository(session)
        self._catalog_repo = CatalogRepository(session)
        self._catalog = CatalogService(self._catalog_repo)

    def readiness(self) -> CommunicationReadinessOut:
        self._catalog.seed_version()  # 409 when no catalog is loaded
        track = next((t for t in self._learning_repo.catalog().tracks if t.key == TRACK_KEY), None)
        topics = list(track.topics) if track else []
        areas = [AreaSpec(t.key, t.title, tuple(t.skills)) for t in topics]
        keys = sorted({s for a in areas for s in a.skills})
        names = {s.key: s.name for s in self._catalog.skills()}
        ids = {s.skill_key: s.id for s, _ in self._catalog_repo.skills(include_inactive=True)}
        states = EvidenceRepository(self._s).states()
        counts = CommunicationRepository(self._s).evidence_counts(keys)
        facts: dict[str, SkillFact] = {}
        for key in keys:
            state = states.get(ids.get(key, -1))
            c = counts.get(key)
            facts[key] = SkillFact(
                score=state.effective_score if state else None,
                measured_rows=c.measured if c else 0,
                manual_rows=c.manual if c else 0,
                other_rows=c.other if c else 0,
                self_reported=bool(c and c.self_reported),
            )
        profile = self._s.get(StartingProfile, 1)
        reported = profile.self_report_json if profile is not None else {}
        out: list[CommunicationAreaOut] = []
        for view in build_readiness_view(areas, facts):
            spec = next(a for a in areas if a.key == view.key)
            out.append(
                CommunicationAreaOut(
                    key=view.key,
                    title=view.title,
                    status=view.status,
                    status_label=STATUS_LABEL[view.status],
                    summary=describe_area(view),
                    skills_total=view.skills_total,
                    skills_with_evidence=view.skills_with_evidence,
                    measured_rows=view.measured_rows,
                    manual_rows=view.manual_rows,
                    other_rows=view.other_rows,
                    self_reported_only=view.self_reported_only,
                    self_report=_self_report_text(view.key, reported),
                    skills=[
                        CommunicationSkillOut(
                            key=s,
                            name=names.get(s, s),
                            score=facts[s].score,
                            level=states[ids[s]].level if ids.get(s) in states else None,
                            confidence=states[ids[s]].confidence if ids.get(s) in states else "NONE",
                            measured=facts[s].measured_rows,
                            manual=facts[s].manual_rows,
                            other=facts[s].other_rows,
                            self_reported=facts[s].self_reported,
                        )
                        for s in spec.skills
                    ],
                )
            )
        return CommunicationReadinessOut(areas=out, note=NOTE)

    def history(self, limit: int = 20) -> SpeakingHistoryOut:
        names = {s.key: s.name for s in self._catalog.skills()}
        rows = []
        for a, p, skill in CommunicationRepository(self._s).history(limit):
            filler_rate = p.metrics_json.get("filler_per_100_words")
            rows.append(
                SpeakingHistoryRowOut(
                    assessment_id=a.id,
                    skill=skill,
                    skill_name=names.get(skill, skill),
                    content_key=a.source_key.removeprefix("content:")
                    if a.source_key.startswith("content:")
                    else None,
                    observed_on=a.observed_on,
                    source=p.source,
                    duration_seconds=p.duration_seconds,
                    word_count=p.word_count,
                    filler_count=p.filler_count,
                    filler_per_100_words=int(filler_rate)
                    if p.source == "BROWSER" and isinstance(filler_rate, int)
                    else None,
                    timed=a.timed,
                    reference_used=a.reference_used,
                    reflection=p.self_reflection,
                )
            )
        return SpeakingHistoryOut(rows=rows, note=HISTORY_NOTE)

    def preview(self, payload: SpeechPreviewIn) -> SpeechPreviewOut:
        """Measure a transcript against the item's targets without storing anything."""
        self._catalog.seed_version()
        item = self._learning_repo.catalog().by_key.get(payload.content_key)
        if item is None:
            raise AppError(ErrorCode.NOT_FOUND, f"Content {payload.content_key!r} not found.", 404)
        if item.type != "interview_question":
            raise AppError(ErrorCode.VALIDATION_ERROR, "Speaking practice needs an interview question.", 422)
        errors = speech_errors("BROWSER", payload.transcript, payload.duration_seconds)
        if errors:
            raise AppError(ErrorCode.VALIDATION_ERROR, "; ".join(errors), 422)
        targets = targets_from_body(item.body.get("speaking"))
        metrics = compute_speaking_metrics(payload.transcript, payload.duration_seconds, targets)
        measured = rate_measured_criteria(metrics, targets)
        return SpeechPreviewOut(content_key=item.key, speaking=_speaking_out("BROWSER", metrics, measured))


def _self_report_text(area_key: str, reported: dict[str, list[str]]) -> str | None:
    """The starting-profile claim for this area, worded as self-report (context only, never a status)."""
    claims = [CLAIM_WORDS[c] for c in CLAIM_WORDS if area_key in reported.get(c, [])]
    if not claims:
        return None
    return f"Self-reported: {', '.join(claims)} (context only, not measured)"
