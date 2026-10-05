from __future__ import annotations

from app.domain.catalog.model import MissionTemplate
from app.domain.catalog.templates import resolve_template


def tpl(key: str, component: str, stages: tuple[str, ...], **kw: object) -> MissionTemplate:
    base: dict[str, object] = dict(
        gap_types=None,
        applies_to=None,
        item_type=None,
        minutes=10,
        minutes_rule=None,
        min_budget=None,
        difficulty=None,
        needs_problem=False,
        observation={"kind": "RECALL_QUIZ"},
        pass_rule="x",
        partial_rule=None,
        output_level=1,
        next_on_pass="GAP_ENGINE",
        next_on_fail="GAP_ENGINE",
    )
    base.update(kw)
    return MissionTemplate(key=key, component=component, stages=stages, **base)  # type: ignore[arg-type]


TEMPLATES = [
    tpl("system_design.timed", "system_design", ("TIMED",)),
    tpl("system_design.drill", "system_design", ("GUIDED", "TIMED"), applies_to=("sd.capacity_estimation",)),
    tpl("system_design.speed", "system_design", ("TIMED",), gap_types=("SPEED",)),
    tpl("system_design.speed_drill", "system_design", ("TIMED",), gap_types=("SPEED",), applies_to=("sd.",)),
    tpl("generic.think_aloud", "generic", ("THINK_ALOUD",)),
]


def resolve(**kw: object) -> tuple[int, str] | None:
    r = resolve_template(TEMPLATES, **kw)  # type: ignore[arg-type]
    return (r.level, r.template.key) if r else None


def test_most_specific_wins_in_documented_order() -> None:
    sd = {"component": "system_design", "stage": "TIMED"}
    assert resolve(**sd, skill_key="sd.capacity_estimation", gap_type="SPEED") == (
        1,
        "system_design.speed_drill",
    )
    assert resolve(**sd, skill_key="sd.capacity_estimation") == (2, "system_design.drill")
    assert resolve(**sd, skill_key="other.skill", gap_type="SPEED") == (3, "system_design.speed")
    assert resolve(**sd, skill_key="other.skill") == (4, "system_design.timed")


def test_generic_fallback_and_missing() -> None:
    assert resolve(component="dsa", stage="THINK_ALOUD", skill_key="trees.traversal") == (
        5,
        "generic.think_aloud",
    )
    assert resolve(component="dsa", stage="TRANSFER", skill_key="trees.traversal") is None


def test_ties_resolve_to_lowest_key() -> None:
    templates = [tpl("dsa.b", "dsa", ("TIMED",)), tpl("dsa.a", "dsa", ("TIMED",))]
    r = resolve_template(templates, component="dsa", stage="TIMED", skill_key="x.y")
    assert r is not None and r.template.key == "dsa.a"
