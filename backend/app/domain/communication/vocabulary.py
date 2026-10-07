"""Closed vocabularies of the communication track (D-087)."""

from __future__ import annotations

from typing import Final

# BROWSER: transcript captured by the browser's speech recognition (measured). MANUAL: no transcript, every
# criterion self-reviewed (weaker evidence, recorded as supported practice).
SPEAKING_SOURCES: Final = ("BROWSER", "MANUAL")

# D-087: optional (T4) communication skills. They never count toward technical readiness recency (G8),
# technical track minutes or the stop list. ``communication.*`` (STAR, follow-ups) is a different,
# required behavioral family and is not covered by this prefix.
OPTIONAL_COMMUNICATION_PREFIX: Final = "comm."


def is_optional_communication_skill(skill: str) -> bool:
    return skill.startswith(OPTIONAL_COMMUNICATION_PREFIX)
