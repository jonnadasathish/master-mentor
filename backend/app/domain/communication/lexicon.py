"""Word lists and version for speaking metrics (D-087). Not part of the frozen ruleset: the metrics only
rate measurable rubric criteria, and every stored row carries ``METRICS_VERSION`` so a change is traceable.

Browser speech recognition often drops hesitation sounds ("um", "uh"), so filler counts are a lower bound.
Ambiguous words ("like", "so") are deliberately not counted: counting them would accuse correct sentences.
"""

from __future__ import annotations

from typing import Final

METRICS_VERSION: Final = "speak-v1"

HESITATION_FILLERS: Final = ("um", "umm", "uh", "uhh", "er", "erm", "ah", "hmm", "mm")
PHRASE_FILLERS: Final = ("you know", "i mean", "kind of", "sort of", "basically", "actually", "literally")

# Phrases that signal a structured spoken answer (order, reason, result, summary).
STRUCTURE_MARKERS: Final = (
    "first",
    "firstly",
    "second",
    "secondly",
    "third",
    "next",
    "then",
    "finally",
    "because",
    "so that",
    "therefore",
    "as a result",
    "for example",
    "for instance",
    "in summary",
    "to summarize",
    "the root cause",
    "the main reason",
    "the impact",
    "the trade-off",
    "the tradeoff",
    "on the other hand",
    "however",
    "my recommendation",
    "the next step",
)

STOPWORDS: Final = frozenset(
    {
        *("a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for", "with"),
        *("is", "are", "was", "were", "be", "been", "it", "this", "that", "i", "we", "you"),
        *("he", "she", "they", "my", "our", "your", "their", "so", "as", "by", "from", "not"),
        *("do", "does", "did", "have", "has", "had", "will", "would", "can", "could", "should"),
    }
)

MAX_TRANSCRIPT_CHARS: Final = 8000
REPEAT_MIN_COUNT: Final = 3
REPEAT_NGRAM_SIZES: Final = (2, 3, 4)
MAX_REPEATED_PHRASES: Final = 3
