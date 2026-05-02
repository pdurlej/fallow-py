from __future__ import annotations

from fnmatch import fnmatch

from .config import PythonConfig
from .graph import ImportGraph
from .models import Action, Issue, Position, Range
from .paths import module_glob_match


def boundary_issues(config: PythonConfig, graph: ImportGraph) -> tuple[list[Issue], set[str]]:
    issues: list[Issue] = []
    paths: set[str] = set()
    if not config.boundary_rules:
        return issues, paths
    for edge in graph.edges:
        source_path = str(edge["path"])
        target_path = str(edge.get("target_path") or "")
        source_module = str(edge["from"])
        target_module = str(edge["to"])
        for rule in config.boundary_rules:
            if not any(_matches(source_path, source_module, pattern) for pattern in rule.from_patterns):
                continue
            matched = next(
                (pattern for pattern in rule.disallow if _matches(target_path, target_module, pattern)),
                None,
            )
            if not matched:
                continue
            paths.add(source_path)
            issues.append(
                Issue(
                    rule="boundary-violation",
                    severity=rule.severity,
                    confidence="high",
                    path=source_path,
                    module=source_module,
                    range=Range(Position(int(edge["line"]), 1), Position(int(edge["line"]), 1)),
                    message=f"Boundary rule '{rule.name}' disallows importing {target_module}.",
                    evidence={
                        "rule": rule.name,
                        "importer_module": source_module,
                        "importer_path": source_path,
                        "imported_module": target_module,
                        "imported_path": target_path,
                        "line": edge["line"],
                        "matched_pattern": matched,
                    },
                    actions=[
                        Action(
                            "move-dependency-behind-boundary",
                            False,
                            "Invert the dependency, extract an interface, or move the import to an allowed layer.",
                        )
                    ],
                )
            )
    return sorted(issues, key=lambda item: (item.path or "", item.range.start.line, item.message)), paths


def _matches(path: str, module: str, pattern: str) -> bool:
    pat = pattern.replace("\\", "/")
    return fnmatch(path, pat) or module_glob_match(module, pat) or fnmatch(module, pat)
