"""Pure prerequisite-graph validation with actionable diagnostics.

Checks (SKILL_GRAPH.md §2):
1. every prerequisite exists;  2. no self-dependency;  3. no cycle (reports the cycle path);
4. no duplicate edge;  5. no required skill depends on an optional skill;  6. depth ≤ limit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.domain.catalog.issues import Issue


@dataclass(frozen=True)
class GraphReport:
    issues: tuple[Issue, ...]
    topological_order: tuple[str, ...] = ()  # prerequisites before dependents; empty if a cycle exists
    depth: Mapping[str, int] = field(default_factory=dict)  # longest prerequisite chain below each node

    @property
    def ok(self) -> bool:
        return not any(issue.is_error for issue in self.issues)

    @property
    def max_depth(self) -> int:
        return max(self.depth.values(), default=0)


def validate_graph(
    nodes: Sequence[str],
    edges: Mapping[str, Sequence[str]],
    *,
    optional_nodes: frozenset[str] = frozenset(),
    max_depth: int | None = None,
    source: str = "skills.yaml",
) -> GraphReport:
    """``edges[node]`` lists the prerequisites of ``node``. ``nodes`` order makes output deterministic."""
    issues: list[Issue] = []
    known = set(nodes)
    clean: dict[str, list[str]] = {}

    for node in nodes:
        seen: set[str] = set()
        clean[node] = []
        for prereq in edges.get(node, ()):
            where = f"{source}: skills[{node}].prerequisites"
            if prereq == node:
                issues.append(Issue("graph.self_reference", where, f"{node} lists itself as a prerequisite"))
            elif prereq not in known:
                issues.append(Issue("graph.missing_node", where, f"{node} requires unknown skill {prereq!r}"))
            elif prereq in seen:
                issues.append(Issue("graph.duplicate_edge", where, f"{node} lists {prereq} more than once"))
            else:
                seen.add(prereq)
                clean[node].append(prereq)
                if node not in optional_nodes and prereq in optional_nodes:
                    issues.append(
                        Issue(
                            "graph.required_depends_on_optional",
                            where,
                            f"required skill {node} depends on optional (T4) skill {prereq}",
                        )
                    )

    cycles = _find_cycles(nodes, clean)
    for cycle in cycles:
        path = " → ".join(cycle + [cycle[0]])
        issues.append(Issue("graph.cycle", source, f"Dependency cycle detected:\n\n    {path}"))
    if cycles:
        return GraphReport(issues=tuple(issues))

    order = _topological_order(nodes, clean)
    depth: dict[str, int] = {}
    for node in order:
        depth[node] = 1 + max((depth[p] for p in clean[node]), default=-1)
    if max_depth is not None:
        for node in nodes:
            if depth[node] > max_depth:
                chain = " → ".join(_deepest_chain(node, clean, depth))
                issues.append(
                    Issue(
                        "graph.too_deep",
                        f"{source}: skills[{node}]",
                        f"prerequisite depth {depth[node]} exceeds limit {max_depth}: {chain}",
                    )
                )
    return GraphReport(issues=tuple(issues), topological_order=tuple(order), depth=depth)


def _find_cycles(nodes: Sequence[str], edges: Mapping[str, Sequence[str]]) -> list[list[str]]:
    """Cycles found by depth-first search (at least one per cyclic component), each rotated to start
    at its smallest key so the report is deterministic."""
    white, grey, black = 0, 1, 2
    color = dict.fromkeys(nodes, white)
    found: dict[tuple[str, ...], list[str]] = {}

    for start in nodes:
        if color[start] != white:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = [start]
        color[start] = grey
        while stack:
            node, index = stack[-1]
            prereqs = edges[node]
            if index < len(prereqs):
                stack[-1] = (node, index + 1)
                nxt = prereqs[index]
                if color[nxt] == white:
                    color[nxt] = grey
                    stack.append((nxt, 0))
                    path.append(nxt)
                elif color[nxt] == grey:
                    cycle = path[path.index(nxt) :]
                    pivot = cycle.index(min(cycle))
                    rotated = cycle[pivot:] + cycle[:pivot]
                    found.setdefault(tuple(rotated), rotated)
            else:
                color[node] = black
                stack.pop()
                path.pop()
    return [found[key] for key in sorted(found)]


def _topological_order(nodes: Sequence[str], edges: Mapping[str, Sequence[str]]) -> list[str]:
    """Kahn's algorithm; ties broken by seed order (deterministic)."""
    index = {node: i for i, node in enumerate(nodes)}
    dependents: dict[str, list[str]] = {node: [] for node in nodes}
    remaining = {node: len(edges[node]) for node in nodes}
    for node in nodes:
        for prereq in edges[node]:
            dependents[prereq].append(node)
    ready = sorted((n for n in nodes if remaining[n] == 0), key=index.__getitem__)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for dependent in dependents[node]:
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                ready.append(dependent)
                ready.sort(key=index.__getitem__)
    return order


def _deepest_chain(node: str, edges: Mapping[str, Sequence[str]], depth: Mapping[str, int]) -> list[str]:
    chain = [node]
    while edges[chain[-1]]:
        chain.append(max(edges[chain[-1]], key=lambda p: (depth[p], p)))
    return chain
