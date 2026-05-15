from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .models import ModuleInfo


@dataclass(slots=True)
class ImportGraph:
    modules: dict[str, ModuleInfo]
    edges: list[dict[str, Any]] = field(default_factory=list)
    adjacency: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


def build_import_graph(modules: dict[str, ModuleInfo], include_tests: bool = False) -> ImportGraph:
    graph = ImportGraph(modules=modules)
    edge_keys: set[tuple[str, str, int, str | None]] = set()
    for module in sorted(modules.values(), key=lambda item: item.module):
        for record in sorted(module.imports, key=lambda item: (item.line, item.raw_module or "", item.imported_symbol or "")):
            if record.classification != "local" or not record.target_module:
                continue
            target = modules.get(record.target_module)
            if not include_tests and (module.is_test or (target and target.is_test)):
                continue
            key = (record.importer, record.target_module, record.line, record.imported_symbol)
            if key in edge_keys:
                continue
            edge_keys.add(key)
            edge = {
                "from": record.importer,
                "to": record.target_module,
                "path": record.path,
                "target_path": record.target_path,
                "line": record.line,
                "imported_symbol": record.imported_symbol,
                "kind": record.kind,
                "confidence": "medium" if record.dynamic else "high",
                "type_checking": record.type_checking,
                "dynamic": record.dynamic,
            }
            graph.edges.append(edge)
            graph.adjacency[record.importer].add(record.target_module)
            graph.reverse[record.target_module].add(record.importer)
            graph.adjacency.setdefault(record.target_module, set())
            graph.reverse.setdefault(record.importer, set())
    return graph


def reachable_from(entry_modules: list[str], graph: ImportGraph, include_type_checking: bool = False) -> set[str]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge["type_checking"] and not include_type_checking:
            continue
        adjacency[edge["from"]].add(edge["to"])
    seen: set[str] = set()
    stack = [module for module in entry_modules if module in graph.modules]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        stack.extend(sorted(adjacency.get(module, set()) - seen, reverse=True))
    return seen


def strongly_connected_components(graph: ImportGraph, include_type_checking: bool = True) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge["type_checking"] and not include_type_checking:
            continue
        adjacency[edge["from"]].append(edge["to"])
    for module in graph.modules:
        adjacency.setdefault(module, [])
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def connect(module: str) -> None:
        nonlocal index
        indices[module] = index
        lowlinks[module] = index
        index += 1
        stack.append(module)
        on_stack.add(module)
        for target in sorted(adjacency[module]):
            if target not in indices:
                connect(target)
                lowlinks[module] = min(lowlinks[module], lowlinks[target])
            elif target in on_stack:
                lowlinks[module] = min(lowlinks[module], indices[target])
        if lowlinks[module] == indices[module]:
            component: list[str] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == module:
                    break
            if len(component) > 1 or module in adjacency[module]:
                components.append(sorted(component))

    for module in sorted(graph.modules):
        if module not in indices:
            connect(module)
    return sorted(components, key=lambda comp: (comp[0], len(comp), comp))


def cycle_path(component: list[str], graph: ImportGraph) -> list[str]:
    comp = set(component)
    start = sorted(comp)[0]
    path = [start]
    current = start
    seen = {start}
    while True:
        candidates = sorted(target for target in graph.adjacency.get(current, set()) if target in comp)
        if not candidates:
            break
        if start in candidates and len(path) > 1:
            path.append(start)
            break
        next_module = next((candidate for candidate in candidates if candidate not in seen), candidates[0])
        path.append(next_module)
        if next_module in seen:
            path.append(start)
            break
        seen.add(next_module)
        current = next_module
        if len(path) > len(comp) + 2:
            break
    if path[-1] != start:
        path.append(start)
    return path


def edge_for(graph: ImportGraph, source: str, target: str) -> dict[str, Any] | None:
    for edge in graph.edges:
        if edge["from"] == source and edge["to"] == target:
            return edge
    return None
