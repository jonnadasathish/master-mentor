"""CALIBRATION mentor message (MENTOR_ENGINE §9 rule 1): the diagnostics sentence exists only when there is
something to list. Never "Today's diagnostics: ." (D-079)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.domain.mentor.messages import r_calibration

TAIL = "No new material until the baseline is complete."


def ctx(*items: tuple[str | None, str, str], mode: bool = True) -> Any:
    """Just what the rule reads: calibration facts and the plan's items (battery key, candidate key, type)."""
    plan_items = [SimpleNamespace(battery_item_key=b, candidate_key=k, candidate_type=t) for b, k, t in items]
    calibration = SimpleNamespace(calibration_mode=mode, assessed_required=8, required=123)
    inputs = SimpleNamespace(calibration=calibration)
    return SimpleNamespace(inputs=inputs, plan=SimpleNamespace(items=plan_items))


def test_one_diagnostic_is_listed() -> None:
    message = r_calibration(ctx(("M0-B03", "BASE:M0-B03", "BASELINE")))
    assert message is not None and message.rule == "CALIBRATION"
    assert message.text == f"Calibration: 8/123 required skills measured. Today's diagnostics: M0-B03. {TAIL}"
    assert message.payload["items"] == ["M0-B03"]


def test_several_diagnostics_are_listed_in_plan_order() -> None:
    message = r_calibration(
        ctx(
            ("M0-B01", "BASE:M0-B01", "BASELINE"),
            ("M0-B02", "BASE:M0-B02", "BASELINE"),
            ("M0-B04", "BASE:M0-B04", "BASELINE"),
        )
    )
    assert message is not None
    assert message.text == (
        f"Calibration: 8/123 required skills measured. Today's diagnostics: M0-B01, M0-B02, M0-B04. {TAIL}"
    )
    assert message.payload["items"] == ["M0-B01", "M0-B02", "M0-B04"]


def test_no_diagnostics_leaves_no_empty_clause() -> None:
    for empty in (ctx(), ctx((None, "GAP:x", "GAP"))):  # no items at all / items that are not diagnostics
        message = r_calibration(empty)
        assert message is not None
        assert message.text == f"Calibration: 8/123 required skills measured. {TAIL}"
        assert "diagnostics" not in message.text and ": ." not in message.text
        assert message.payload["items"] == []


def test_non_battery_diagnostic_candidates_are_used_when_no_battery_item_exists() -> None:
    message = r_calibration(ctx((None, "DIAG:engineering.debugging", "DIAGNOSTIC")))
    assert message is not None
    assert "Today's diagnostics: DIAG:engineering.debugging." in message.text


def test_outside_calibration_there_is_no_message() -> None:
    assert r_calibration(ctx(("M0-B01", "BASE:M0-B01", "BASELINE"), mode=False)) is None


def test_same_inputs_give_the_same_message() -> None:
    items = (("M0-B01", "BASE:M0-B01", "BASELINE"), ("M0-B02", "BASE:M0-B02", "BASELINE"))
    assert r_calibration(ctx(*items)) == r_calibration(ctx(*items))
