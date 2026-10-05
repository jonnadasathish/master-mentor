from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import MappingProxyType

import pytest

from app.domain.canonical import canonical_json, sha256_hex


def test_key_order_does_not_matter() -> None:
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1}) == '{"a":2,"b":1}'


def test_tuples_lists_and_mapping_proxies_are_equivalent() -> None:
    assert canonical_json((1, 2)) == canonical_json([1, 2])
    assert canonical_json(MappingProxyType({"k": (1,)})) == canonical_json({"k": [1]})


def test_sets_are_sorted() -> None:
    assert canonical_json({3, 1, 2}) == "[1,2,3]"


def test_decimal_has_one_form() -> None:
    assert canonical_json(Decimal("1.50")) == canonical_json(Decimal("1.5")) == '"1.5"'
    assert canonical_json(Decimal("100")) == '"100"'


def test_dates_and_aware_datetimes() -> None:
    assert canonical_json(date(2026, 10, 4)) == '"2026-10-04"'
    assert canonical_json(datetime(2026, 10, 4, 1, 2, tzinfo=UTC)) == '"2026-10-04T01:02:00+00:00"'


@pytest.mark.parametrize("bad", [1.5, datetime(2026, 10, 4), Decimal("NaN"), object()])
def test_non_deterministic_values_rejected(bad: object) -> None:
    with pytest.raises(TypeError):
        canonical_json(bad)


def test_hash_is_stable_sha256() -> None:
    assert sha256_hex({"a": 1}) == sha256_hex({"a": 1})
    assert len(sha256_hex({"a": 1})) == 64
    assert sha256_hex({"a": 1}) != sha256_hex({"a": 2})
