"""Deterministic speaking metrics and the 0/1/2 rating of the measurable rubric criteria (D-087).

These checks measure only what a transcript can show: length, duration, filler words, structure markers,
target vocabulary and repeated phrases. They do not judge grammar, pronunciation, accent or pauses, and the
caller must never present them as such. Integer arithmetic only.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.domain.communication import lexicon
from app.domain.learning.grading import share_points

MIN_SPOKEN_WORDS = 5  # a browser transcript shorter than this is not a speaking practice
MAX_PLAUSIBLE_WPM = 300  # faster than this is a mismatch between the transcript and the claimed duration
MAX_SPEAKING_SECONDS = 3600

_WORD = re.compile(r"[a-z0-9']+")
_SENTENCE_END = re.compile(r"[.!?]+")


@dataclass(frozen=True)
class SpeakingTargets:
    """Per-exercise targets, seed data of the content item (``body.speaking``). Zero/empty = not measured."""

    target_seconds: int = 0
    min_words: int = 0
    max_words: int = 0
    max_filler_per_100: int = 0
    structure_markers_min: int = 0
    vocabulary: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpeakingMetrics:
    metrics_version: str
    word_count: int
    sentence_count: int | None  # None: the browser transcript carried no punctuation
    duration_seconds: int
    words_per_minute: int | None
    filler_count: int
    filler_per_100_words: int
    fillers: tuple[tuple[str, int], ...]
    structure_markers: tuple[str, ...]
    vocabulary_used: tuple[str, ...]
    vocabulary_missing: tuple[str, ...]
    repeated_phrases: tuple[tuple[str, int], ...]


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("’", "'"))


def _count_phrase(tokens: Sequence[str], phrase: str) -> int:
    parts = phrase.split()
    n = len(parts)
    return sum(1 for i in range(len(tokens) - n + 1) if list(tokens[i : i + n]) == parts)


def _repeated_phrases(tokens: Sequence[str]) -> tuple[tuple[str, int], ...]:
    found: dict[str, int] = {}
    for size in lexicon.REPEAT_NGRAM_SIZES:
        counts = Counter(" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1))
        for phrase, count in counts.items():
            parts = phrase.split()
            if count >= lexicon.REPEAT_MIN_COUNT and any(p not in lexicon.STOPWORDS for p in parts):
                found[phrase] = count
    # Drop a phrase that is only a part of a longer repeated phrase with the same count.
    kept = {p: c for p, c in found.items() if not any(p != q and p in q and found[q] >= c for q in found)}
    ranked = sorted(kept.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    return tuple(ranked[: lexicon.MAX_REPEATED_PHRASES])


NO_TARGETS = SpeakingTargets()


def compute_speaking_metrics(
    transcript: str, duration_seconds: int, targets: SpeakingTargets = NO_TARGETS
) -> SpeakingMetrics:
    text = transcript[: lexicon.MAX_TRANSCRIPT_CHARS]
    tokens = tokenize(text)
    words = len(tokens)
    fillers: dict[str, int] = {}
    for f in lexicon.HESITATION_FILLERS:
        n = sum(1 for t in tokens if t == f)
        if n:
            fillers[f] = n
    for f in lexicon.PHRASE_FILLERS:
        n = _count_phrase(tokens, f)
        if n:
            fillers[f] = n
    filler_total = sum(fillers.values())
    segments = [s for s in _SENTENCE_END.split(text) if tokenize(s)]
    punctuated = bool(_SENTENCE_END.search(text))
    markers = tuple(m for m in lexicon.STRUCTURE_MARKERS if _count_phrase(tokens, m) > 0)
    used = tuple(v for v in targets.vocabulary if _count_phrase(tokens, v.lower()) > 0)
    missing = tuple(v for v in targets.vocabulary if v not in used)
    return SpeakingMetrics(
        metrics_version=lexicon.METRICS_VERSION,
        word_count=words,
        sentence_count=len(segments) if punctuated else None,
        duration_seconds=duration_seconds,
        words_per_minute=(words * 60 // duration_seconds) if duration_seconds > 0 else None,
        filler_count=filler_total,
        filler_per_100_words=(filler_total * 100 // words) if words else 0,
        fillers=tuple(sorted(fillers.items(), key=lambda kv: (-kv[1], kv[0]))),
        structure_markers=markers,
        vocabulary_used=used,
        vocabulary_missing=missing,
        repeated_phrases=_repeated_phrases(tokens),
    )


# ------------------------------------------------------------------------------------------ criteria

MEASURED_CRITERIA: tuple[str, ...] = (
    "length",
    "duration",
    "fillers",
    "structure",
    "vocabulary",
    "repetition",
)


def _band(value: int, full: tuple[int, int], partial: tuple[int, int]) -> int:
    if full[0] <= value <= full[1]:
        return 2
    return 1 if partial[0] <= value <= partial[1] else 0


def rate_measured_criteria(m: SpeakingMetrics, t: SpeakingTargets) -> dict[str, int]:
    """Rating 0 (missed), 1 (partly), 2 (fully) for every criterion the targets make measurable."""
    out: dict[str, int] = {}
    if t.min_words > 0 or t.max_words > 0:
        low, high = t.min_words, t.max_words or 10**9
        out["length"] = _band(m.word_count, (low, high), (low * 6 // 10, high * 3 // 2))
    if t.target_seconds > 0:
        s = t.target_seconds
        out["duration"] = _band(m.duration_seconds * 100, (s * 75, s * 125), (s * 50, s * 150))
    if t.max_filler_per_100 > 0:
        r = m.filler_per_100_words
        out["fillers"] = 2 if r <= t.max_filler_per_100 else (1 if r <= t.max_filler_per_100 * 2 else 0)
    if t.structure_markers_min > 0:
        hits, need = len(m.structure_markers), t.structure_markers_min
        out["structure"] = 2 if hits >= need else (1 if hits * 2 >= need else 0)
    if t.vocabulary:
        share = len(m.vocabulary_used) * 100 // len(t.vocabulary)
        out["vocabulary"] = 2 if share >= 70 else (1 if share >= 40 else 0)
    if out:  # repetition is rated only together with at least one measured target
        n = len(m.repeated_phrases)
        out["repetition"] = 2 if n == 0 else (1 if n == 1 else 0)
    return out


def speaking_points(measured: Mapping[str, int], self_rated: Mapping[str, tuple[int, int]]) -> int:
    """Integer 0-100 points: every measured criterion weighs 1, every self-rated rubric criterion weighs its
    seed points. ``self_rated`` maps a key to (rating 0..2, points)."""
    earned = [(rating, 1) for rating in measured.values()]
    earned += [(rating, weight) for rating, weight in self_rated.values()]
    return share_points(earned)


def targets_from_body(speaking: Mapping[str, Any] | None) -> SpeakingTargets:
    """The seed ``body.speaking`` mapping of a content item (validated at seed time)."""
    if not speaking:
        return NO_TARGETS
    return SpeakingTargets(
        target_seconds=int(speaking.get("target_seconds", 0)),
        min_words=int(speaking.get("min_words", 0)),
        max_words=int(speaking.get("max_words", 0)),
        max_filler_per_100=int(speaking.get("max_filler_per_100", 0)),
        structure_markers_min=int(speaking.get("structure_markers_min", 0)),
        vocabulary=tuple(str(v) for v in speaking.get("vocabulary", ())),
    )


def speech_errors(source: str, transcript: str | None, duration_seconds: int) -> list[str]:
    """Server-side checks of what the browser claims. The client never sends metrics or scores; these checks
    only reject a transcript/duration pair that cannot be a real attempt."""
    if source == "MANUAL":
        return ["a manual practice carries no transcript"] if transcript else []
    if source != "BROWSER":
        return [f"unknown speaking source {source!r}"]
    errors: list[str] = []
    words = len(tokenize(transcript or ""))
    if words < MIN_SPOKEN_WORDS:
        errors.append(f"the transcript needs at least {MIN_SPOKEN_WORDS} words")
    if not 1 <= duration_seconds <= MAX_SPEAKING_SECONDS:
        errors.append(f"duration must be between 1 and {MAX_SPEAKING_SECONDS} seconds")
    elif words * 60 > MAX_PLAUSIBLE_WPM * duration_seconds:
        errors.append("the transcript is too long for the recorded duration")
    return errors
