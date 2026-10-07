"""Speaking metrics and Communication Readiness view (D-087): deterministic, integer, honest about limits."""

from __future__ import annotations

from app.domain.communication.metrics import (
    SpeakingTargets,
    compute_speaking_metrics,
    rate_measured_criteria,
    speaking_points,
)
from app.domain.communication.readiness_view import AreaSpec, SkillFact, build_readiness_view

TARGETS = SpeakingTargets(
    target_seconds=60,
    min_words=30,
    max_words=120,
    max_filler_per_100=5,
    structure_markers_min=3,
    vocabulary=("root cause", "rollback"),
)
GOOD = (
    "First, the root cause was a missing index on the orders table. Because the query scanned every row, "
    "checkout slowed down. Then we added the index and measured the result. Finally we rolled back nothing "
    "and the rollback plan stayed unused. The latency dropped from two seconds to forty milliseconds today."
)


def test_metrics_are_deterministic_and_integer() -> None:
    a = compute_speaking_metrics(GOOD, 55, TARGETS)
    assert a == compute_speaking_metrics(GOOD, 55, TARGETS)
    assert isinstance(a.word_count, int) and isinstance(a.words_per_minute, int)
    assert a.sentence_count == 5 and a.metrics_version == "speak-v1"


def test_fillers_structure_vocabulary_and_repeats() -> None:
    text = "Um so basically the cache, you know, the cache the cache the cache helps. The root cause is clear"
    m = compute_speaking_metrics(text, 30, TARGETS)
    assert dict(m.fillers) == {"um": 1, "you know": 1, "basically": 1}
    assert m.vocabulary_used == ("root cause",) and m.vocabulary_missing == ("rollback",)
    assert any(p.startswith("the cache") for p, _ in m.repeated_phrases)
    assert m.filler_per_100_words == m.filler_count * 100 // m.word_count


def test_ambiguous_words_are_not_counted_as_fillers() -> None:
    m = compute_speaking_metrics("I like this design so we keep it", 10)
    assert m.filler_count == 0


def test_unpunctuated_browser_transcript_has_no_sentence_count() -> None:
    m = compute_speaking_metrics("we added an index and the query got faster", 10)
    assert m.sentence_count is None and m.word_count == 9


def test_empty_transcript_and_zero_duration_do_not_divide_by_zero() -> None:
    m = compute_speaking_metrics("", 0, TARGETS)
    assert (m.word_count, m.filler_per_100_words, m.words_per_minute) == (0, 0, None)


def test_measured_ratings_follow_the_targets() -> None:
    m = compute_speaking_metrics(GOOD, 55, TARGETS)
    r = rate_measured_criteria(m, TARGETS)
    assert r["duration"] == 2 and r["structure"] == 2 and r["vocabulary"] == 2 and r["fillers"] == 2
    assert rate_measured_criteria(m, SpeakingTargets()) == {}  # nothing measurable without targets


def test_short_answer_is_rated_partly_or_missed_on_length() -> None:
    m = compute_speaking_metrics("we added an index", 5, TARGETS)
    r = rate_measured_criteria(m, TARGETS)
    assert r["length"] == 0 and r["duration"] == 0


def test_points_mix_measured_and_self_rated_with_half_up_rounding() -> None:
    assert speaking_points({"length": 2, "fillers": 2}, {"clarity": (2, 2)}) == 100
    assert speaking_points({"length": 0}, {"clarity": (2, 1)}) == 50
    assert speaking_points({}, {}) == 0
    assert speaking_points({"a": 1, "b": 0, "c": 0}, {}) == 17  # 1/6 -> 16.67 -> 17


def test_readiness_view_keeps_evidence_basis_apart_and_has_no_overall() -> None:
    areas = (AreaSpec("fluency", "Fluency", ("a", "b")), AreaSpec("writing", "Writing", ("c",)))
    facts = {
        "a": SkillFact(score=60, measured_rows=2, manual_rows=1, other_rows=0, self_reported=True),
        "b": SkillFact(score=None, measured_rows=0, manual_rows=0, other_rows=0, self_reported=True),
        "c": SkillFact(score=None, measured_rows=0, manual_rows=0, other_rows=0, self_reported=False),
    }
    fluency, writing = build_readiness_view(areas, facts)
    assert (fluency.status, fluency.measured_rows, fluency.manual_rows) == ("WORKING", 2, 1)
    assert (fluency.skills_with_evidence, fluency.self_reported_only) == (1, 1)
    assert writing.status == "NOT_STARTED" and writing.self_reported_only == 0
