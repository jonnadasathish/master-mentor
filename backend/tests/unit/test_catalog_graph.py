from __future__ import annotations

from app.domain.catalog.graph import validate_graph


def codes(report: object) -> list[str]:
    return [i.code for i in report.issues]  # type: ignore[attr-defined]


def test_valid_graph_has_topological_order_and_depth() -> None:
    report = validate_graph(["a.x", "b.y", "c.z"], {"b.y": ["a.x"], "c.z": ["b.y", "a.x"]})
    assert report.ok
    assert report.topological_order == ("a.x", "b.y", "c.z")
    assert report.depth == {"a.x": 0, "b.y": 1, "c.z": 2}
    assert report.max_depth == 2


def test_cycle_reports_the_path() -> None:
    report = validate_graph(["a.a", "b.b", "c.c"], {"a.a": ["b.b"], "b.b": ["c.c"], "c.c": ["a.a"]})
    assert codes(report) == ["graph.cycle"]
    assert "a.a → b.b → c.c → a.a" in report.issues[0].message
    assert report.topological_order == ()


def test_cycle_report_is_deterministic_regardless_of_entry_point() -> None:
    edges = {"a.a": ["b.b"], "b.b": ["c.c"], "c.c": ["a.a"]}
    first = validate_graph(["c.c", "b.b", "a.a"], edges).issues
    second = validate_graph(["a.a", "b.b", "c.c"], edges).issues
    assert [i.message for i in first] == [i.message for i in second]


def test_self_reference() -> None:
    report = validate_graph(["a.a"], {"a.a": ["a.a"]})
    assert codes(report) == ["graph.self_reference"]
    assert "a.a lists itself" in report.issues[0].message


def test_missing_node() -> None:
    report = validate_graph(["a.a"], {"a.a": ["ghost.skill"]})
    assert codes(report) == ["graph.missing_node"]
    assert "ghost.skill" in report.issues[0].message


def test_duplicate_edge() -> None:
    assert codes(validate_graph(["a.a", "b.b"], {"b.b": ["a.a", "a.a"]})) == ["graph.duplicate_edge"]


def test_depth_limit_reports_the_chain() -> None:
    nodes = [f"n.{i}" for i in range(5)]
    edges = {f"n.{i}": [f"n.{i - 1}"] for i in range(1, 5)}
    assert validate_graph(nodes, edges, max_depth=4).ok
    report = validate_graph(nodes, edges, max_depth=3)
    assert codes(report) == ["graph.too_deep"]
    assert "n.4 → n.3 → n.2 → n.1 → n.0" in report.issues[0].message


def test_required_skill_must_not_depend_on_optional() -> None:
    report = validate_graph(["opt.x", "req.y"], {"req.y": ["opt.x"]}, optional_nodes=frozenset({"opt.x"}))
    assert codes(report) == ["graph.required_depends_on_optional"]
    # optional depending on optional is fine
    assert validate_graph(["o.a", "o.b"], {"o.b": ["o.a"]}, optional_nodes=frozenset({"o.a", "o.b"})).ok
