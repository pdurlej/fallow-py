from __future__ import annotations

import ast
from statistics import mean
from typing import Any

from .config import PythonConfig
from .graph import ImportGraph
from .models import Action, FunctionInfo, Issue, ModuleInfo, Position, Range


def analyze_complexity(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
    graph: ImportGraph,
    duplicate_paths: set[str],
    cycle_modules: set[str],
    boundary_paths: set[str],
) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    function_metrics: list[dict[str, Any]] = []
    file_scores: dict[str, int] = {}
    for module in sorted(modules.values(), key=lambda item: item.path):
        if module.parse_error:
            continue
        if module.is_test and not config.include_tests:
            continue
        file_score = 0
        if config.health.enabled and module.line_count > config.health.max_file_lines:
            issues.append(
                Issue(
                    rule="large-file",
                    severity="info",
                    confidence="high",
                    path=module.path,
                    module=module.module,
                    range=Range(Position(1, 1), Position(module.line_count, 1)),
                    message=f"File has {module.line_count} lines, above configured maximum {config.health.max_file_lines}.",
                    evidence={"line_count": module.line_count, "threshold": config.health.max_file_lines},
                    actions=[Action("split-file", False, "Consider splitting unrelated responsibilities into smaller modules.")],
                )
            )
            file_score += 10
        for raw in module.functions:
            node = raw.ast_node
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            cyclomatic = cyclomatic_complexity(node)
            cognitive = cognitive_complexity(node)
            lines = raw.end_line - raw.line + 1
            metric = {
                "path": module.path,
                "module": module.module,
                "symbol": raw.name,
                "line": raw.line,
                "end_line": raw.end_line,
                "cyclomatic": cyclomatic,
                "cognitive": cognitive,
                "lines": lines,
            }
            function_metrics.append(metric)
            file_score += max(0, cyclomatic - 1) + max(0, cognitive - 1) + max(0, lines // 40)
            if config.health.enabled and cyclomatic > config.health.max_cyclomatic:
                issues.append(
                    _complexity_issue(
                        "high-cyclomatic-complexity",
                        module,
                        raw,
                        cyclomatic,
                        config.health.max_cyclomatic,
                        "Cyclomatic complexity is above the configured threshold.",
                        "reduce-branches",
                    )
                )
            if config.health.enabled and cognitive > config.health.max_cognitive:
                issues.append(
                    _complexity_issue(
                        "high-cognitive-complexity",
                        module,
                        raw,
                        cognitive,
                        config.health.max_cognitive,
                        "Cognitive complexity approximation is above the configured threshold.",
                        "simplify-nesting",
                    )
                )
            if config.health.enabled and lines > config.health.max_function_lines:
                issues.append(
                    Issue(
                        rule="large-function",
                        severity="info",
                        confidence="high",
                        path=module.path,
                        module=module.module,
                        symbol=raw.name,
                        range=Range(Position(raw.line, raw.column), Position(raw.end_line, raw.end_column)),
                        message=f"Function '{raw.name}' has {lines} lines, above configured maximum {config.health.max_function_lines}.",
                        evidence={"line_count": lines, "threshold": config.health.max_function_lines},
                        actions=[Action("split-function", False, "Extract cohesive chunks and isolate side effects.")],
                    )
                )
        fan_out = len(graph.adjacency.get(module.module, set()))
        fan_in = len(graph.reverse.get(module.module, set()))
        file_score += min(20, fan_out * 2)
        if module.path in duplicate_paths:
            file_score += 12
        if module.module in cycle_modules:
            file_score += 15
        if module.path in boundary_paths:
            file_score += 15
        file_scores[module.path] = file_score
        if config.health.enabled and file_score >= config.health.hotspot_score_threshold:
            instability = fan_out / (fan_in + fan_out) if fan_in + fan_out else 0.0
            issues.append(
                Issue(
                    rule="risky-hotspot",
                    severity="warning",
                    confidence="medium",
                    path=module.path,
                    module=module.module,
                    range=Range(Position(1, 1), Position(max(1, module.line_count), 1)),
                    message=f"File has overlapping risk signals with hotspot score {file_score}.",
                    evidence={
                        "score": file_score,
                        "fan_in": fan_in,
                        "fan_out": fan_out,
                        "instability": round(instability, 3),
                        "in_cycle": module.module in cycle_modules,
                        "duplicate_involved": module.path in duplicate_paths,
                        "boundary_violation": module.path in boundary_paths,
                    },
                    actions=[
                        Action(
                            "inspect-before-editing",
                            True,
                            "Inspect this file before broad edits because several static risk signals overlap.",
                        )
                    ],
                )
            )
    metrics = _summary_metrics(function_metrics, graph, file_scores)
    return issues, metrics


def cyclomatic_complexity(node: ast.AST) -> int:
    score = 1
    for child in _walk_function_body(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.IfExp, ast.Assert)):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(0, len(child.values) - 1)
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            score += 1 + len(child.generators)
        elif isinstance(child, ast.Match):
            score += len(child.cases)
    return score


def cognitive_complexity(node: ast.AST) -> int:
    def visit(item: ast.AST, nesting: int, root: bool = False) -> int:
        if not root and isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return 0
        total = 0
        branch_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.IfExp, ast.Match)
        if isinstance(item, branch_nodes):
            total += 1 + nesting
            nesting += 1
        if isinstance(item, ast.BoolOp):
            total += max(0, len(item.values) - 1)
        if isinstance(item, (ast.Break, ast.Continue, ast.Raise)):
            total += 1
        for child in ast.iter_child_nodes(item):
            total += visit(child, nesting)
        return total

    return visit(node, 0, root=True)


def _walk_function_body(node: ast.AST):
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        yield child
        stack.extend(ast.iter_child_nodes(child))


def _complexity_issue(
    rule: str,
    module: ModuleInfo,
    raw: FunctionInfo,
    value: int,
    threshold: int,
    message: str,
    action_type: str,
) -> Issue:
    return Issue(
        rule=rule,
        severity="warning",
        confidence="high",
        path=module.path,
        module=module.module,
        symbol=raw.name,
        range=Range(Position(raw.line, raw.column), Position(raw.end_line, raw.end_column)),
        message=f"{message} {raw.name}={value}, threshold={threshold}.",
        evidence={"value": value, "threshold": threshold, "approximation": rule == "high-cognitive-complexity"},
        actions=[Action(action_type, False, "Split decision logic, extract policy objects, or isolate side effects.")],
    )


def _summary_metrics(
    functions: list[dict[str, Any]],
    graph: ImportGraph,
    file_scores: dict[str, int],
) -> dict[str, Any]:
    cyclomatic = [item["cyclomatic"] for item in functions]
    cognitive = [item["cognitive"] for item in functions]
    top_hotspots = [
        {"path": path, "score": score}
        for path, score in sorted(file_scores.items(), key=lambda item: (-item[1], item[0]))[:20]
    ]
    return {
        "average_cyclomatic_complexity": round(mean(cyclomatic), 2) if cyclomatic else 0.0,
        "average_cognitive_complexity": round(mean(cognitive), 2) if cognitive else 0.0,
        "max_cyclomatic_complexity": max(cyclomatic) if cyclomatic else 0,
        "max_cognitive_complexity": max(cognitive) if cognitive else 0,
        "module_count": len(graph.modules),
        "edge_count": len(graph.edges),
        "cycle_count": 0,
        "functions": sorted(functions, key=lambda item: (-item["cyclomatic"], -item["cognitive"], item["path"], item["line"]))[:50],
        "top_hotspots": top_hotspots,
    }
