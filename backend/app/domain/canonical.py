"""Canonical, deterministic serialization used for hashing (input hashes, ruleset fingerprints).

The same logical value always produces the same bytes: mapping keys are sorted, tuples and lists are
identical, dates use ISO format. Floats are rejected (domain math is integer/Decimal, CLAUDE.md rule 10).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Set
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

type JsonValue = None | bool | int | str | list[JsonValue] | dict[str, JsonValue]


def to_canonical(value: object) -> JsonValue:
    """Convert a domain value into a JSON-compatible value with a single canonical form."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        raise TypeError("floats are not allowed in deterministic domain values; use int or Decimal")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise TypeError("non-finite Decimal values are not allowed")
        return format(value.normalize(), "f")  # 1.50 -> "1.5", 100 -> "100"
    if isinstance(value, Enum):
        return to_canonical(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise TypeError("naive datetimes are not allowed; use UTC-aware datetimes")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {_key(k): to_canonical(v) for k, v in value.items()}
    if isinstance(value, Set):
        items = [to_canonical(v) for v in value]
        return sorted(items, key=lambda item: canonical_json(item))
    if isinstance(value, list | tuple):
        return [to_canonical(v) for v in value]
    raise TypeError(f"unsupported type for canonical serialization: {type(value).__name__}")


def _key(key: object) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, bool) or not isinstance(key, int | Enum):
        raise TypeError(f"unsupported mapping key type: {type(key).__name__}")
    return str(key.value if isinstance(key, Enum) else key)


def canonical_json(value: object) -> str:
    return json.dumps(to_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
