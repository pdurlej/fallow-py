from __future__ import annotations

import time
from typing import Any

from .ast_index import index_file
from .boundaries import boundary_issues
from .complexity import analyze_complexity
from .config import PythonConfig
from .context import AnalysisContext
from .dead_code import dead_code_issues, detect_entrypoints
from .dependencies import (
    classify_imports,
    dependency_issues,
    entrypoints_from_packaging,
    parse_dependency_declarations,
)
from .diff import resolve_since
from .discovery import discover_python_files, discover_source_roots
from .dupes import duplicate_issues
from .fingerprints import assign_fingerprints
from .frameworks import detect_frameworks
from .graph import build_import_graph, cycle_path, edge_for, strongly_connected_components
from .models import CONFIDENCE_ORDER, RULES, SEVERITY_ORDER, Action, ExportRecord, ImportRecord, Issue, ModuleInfo, Position, Range, SCHEMA_VERSION, VERSION
from .paths import normalize_package_name, relpath
from .resolver import ModuleResolver
from .suppressions import apply_suppressions
from .summary import summary_from_issue_dicts


LIMITATIONS = [
    "Dynamic imports are resolved only when the module name is a string literal.",
    "Runtime monkey patching and reflection are not modeled.",
    "Plugin systems, dependency injection containers, and runtime path mutation may hide real usage.",
    "Framework-specific magic is handled conservatively and may require explicit entrypoint config.",
    "Namespace package ambiguity is resolved by source-root preference and may need config in unusual layouts.",
    "Conditional imports are classified statically and may differ across deployment environments.",
    "Generated code is skipped only when obvious markers or common generated filenames are present.",
]


def analyze(config: PythonConfig) -> dict[str, Any]:
    started = time.perf_counter()
    source_roots = discover_source_roots(config)
    files = discover_python_files(config, source_roots)
    resolver = ModuleResolver(config.root, source_roots)
    modules: dict[str, ModuleInfo] = {}
    module_ambiguities: list[dict[str, Any]] = []
    initial_issues: list[Issue] = []

    for path in files:
        module_name, source_root, is_init = resolver.module_name_for_path(path)
        info = index_file(path, config.root, module_name, source_root, is_init)
        if module_name in modules:
            existing = modules[module_name]
            module_ambiguities.append(
                {
                    "module": module_name,
                    "selected_path": existing.path,
                    "shadowed_path": info.path,
                    "selected_source_root": existing.source_root,
                    "shadowed_source_root": info.source_root,
                    "reason": "Multiple configured source roots map files to the same module name; the first deterministic path was used.",
                }
            )
            continue
        modules[info.module] = info
        resolver.register(info)

    for info in modules.values():
        for record in info.imports:
            resolver.resolve_import(record, info.is_package_init)
    _refresh_alias_maps(modules)
    _build_export_records(config, modules)

    all_imports = [record for info in modules.values() for record in info.imports]
    classify_imports(all_imports, config)
    declarations = parse_dependency_declarations(config.root)
    declared_packages = {
        normalize_package_name(name)
        for name in [*declarations.runtime, *declarations.optional, *declarations.dev]
    }
    frameworks = detect_frameworks(modules, declared_packages) if config.framework_heuristics else []
    graph = build_import_graph(modules, include_tests=config.include_tests)

    initial_issues.extend(_config_error_issues(config))
    initial_issues.extend(_parse_error_issues(modules))
    initial_issues.extend(_import_issues(all_imports))
    initial_issues.extend(_production_test_import_issues(config, all_imports, modules))

    entries, entry_modules, explicit_entrypoints, entrypoint_symbols = detect_entrypoints(
        config, modules, entrypoints_from_packaging(declarations)
    )
    context = AnalysisContext(
        config=config,
        source_roots=tuple(source_roots),
        modules=modules,
        graph=graph,
        declarations=declarations,
        entrypoints=tuple(entries),
        entry_modules=tuple(entry_modules),
        explicit_entrypoints=explicit_entrypoints,
        entrypoint_symbols={key: frozenset(value) for key, value in entrypoint_symbols.items()},
    )
    _apply_module_states(context)
    cycle_components = strongly_connected_components(graph)
    cycle_issues, cycle_graphs, cycle_modules = _cycle_issues(cycle_components, graph, modules)
    initial_issues.extend(cycle_issues)

    boundary, boundary_paths = boundary_issues(config, graph)
    dupes, duplicate_groups, duplicate_paths = duplicate_issues(config, modules)
    initial_issues.extend(boundary)
    initial_issues.extend(dupes)
    initial_issues.extend(dependency_issues(config, declarations, all_imports))
    initial_issues.extend(
        dead_code_issues(config, modules, graph, entry_modules, explicit_entrypoints)
    )
    _mark_entrypoint_symbols_used(initial_issues, entrypoint_symbols)
    health_issues, metrics = analyze_complexity(
        config, modules, graph, duplicate_paths, cycle_modules, boundary_paths
    )
    metrics["cycle_count"] = len(cycle_components)
    initial_issues.extend(health_issues)

    suppressions = [suppression for info in modules.values() for suppression in info.suppressions]
    active_issues, stale_issues = apply_suppressions(initial_issues, suppressions)
    issues = active_issues + stale_issues
    assign_fingerprints(issues)
    issues = sorted(issues, key=_issue_sort_key)
    diff_scope = _diff_scope_default(config)
    if config.since_ref:
        issues, duplicate_groups, cycle_graphs, diff_scope = _apply_diff_scope(
            config,
            issues,
            modules,
            duplicate_groups,
            cycle_graphs,
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    result = {
        "tool": "fallow",
        "language": "python",
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "root": ".",
        "config_path": relpath(config.config_path, config.root) if config.config_path else None,
        "generated_at": None,
        "analysis": {
            "files_analyzed": len(files),
            "modules_analyzed": len(modules),
            "symbols_indexed": sum(len(info.symbols) for info in modules.values()),
            "imports_indexed": len(all_imports),
            "entrypoints": entries,
            "frameworks_detected": frameworks,
            "source_roots": [relpath(path, config.root) for path in source_roots],
            "dependency_files": sorted(declarations.files),
            "changed_only": {
                "requested": config.changed_only_requested,
                "effective": config.changed_only_effective,
                "reason": _changed_only_reason(config),
            },
            "diff_scope": diff_scope,
            "warnings": config.analysis_warnings,
            "module_ambiguities": sorted(module_ambiguities, key=lambda item: (item["module"], item["shadowed_path"])),
            "duration_ms": duration_ms,
        },
        "summary": _summary(issues, duplicate_groups),
        "issues": [issue.to_dict() for issue in issues],
        "metrics": metrics,
        "graphs": {
            "modules": [info.to_graph_node() for info in sorted(modules.values(), key=lambda item: item.module)],
            "edges": sorted(graph.edges, key=lambda item: (item["from"], item["to"], item["line"])),
            "cycles": cycle_graphs,
            "duplicate_groups": duplicate_groups,
            "exports": [
                {
                    "module": info.module,
                    "path": info.path,
                    **record.to_dict(),
                }
                for info in sorted(modules.values(), key=lambda item: item.module)
                for record in sorted(info.export_records, key=lambda item: (item.name, item.line, item.source))
            ],
        },
        "config": {
            "boundary_rules_configured": bool(config.boundary_rules),
            "include_tests": config.include_tests,
            "framework_heuristics": config.framework_heuristics,
        },
        "limitations": LIMITATIONS,
    }
    return result


def _refresh_alias_maps(modules: dict[str, ModuleInfo]) -> None:
    for info in modules.values():
        for record in info.imports:
            if record.classification != "local" or not record.target_module:
                continue
            if record.kind == "import":
                local_name = record.alias or (record.raw_module or record.target_module).split(".", 1)[0]
                info.alias_to_module[local_name] = record.target_module
            elif record.imported_symbol:
                local_name = record.alias or record.imported_symbol
                info.alias_to_symbol[local_name] = (record.target_module, record.imported_symbol)
            else:
                local_name = record.alias or record.target_module.rsplit(".", 1)[-1]
                info.alias_to_module[local_name] = record.target_module


def _build_export_records(config: PythonConfig, modules: dict[str, ModuleInfo]) -> None:
    init_export_confidence = config.dead_code.confidence_for_init_exports
    for info in modules.values():
        if not info.is_package_init or info.parse_error:
            continue
        explicit_names = {record.name for record in info.export_records if record.source.startswith("__all__")}
        explicit_complete = any(record.source == "__all__" and record.complete for record in info.export_records)
        for record in info.imports:
            if record.classification != "local" or not record.target_module:
                continue
            if record.imported_symbol == "*":
                target = modules.get(record.target_module)
                if not target:
                    continue
                target_exports = [item for item in target.export_records if item.origin_symbol]
                if target_exports:
                    for target_export in target_exports:
                        _add_export_record(
                            info,
                            modules,
                            ExportRecord(
                                name=target_export.name,
                                line=record.line,
                                source="star-reexport",
                                confidence=_known_init_export_confidence(init_export_confidence, target_export.confidence),
                                complete=target_export.complete,
                                origin_module=target_export.origin_module,
                                origin_symbol=target_export.origin_symbol,
                                explicit=target_export.name in explicit_names,
                            ),
                        )
                elif target.exports:
                    for name in sorted(target.exports):
                        _add_export_record(
                            info,
                            modules,
                            ExportRecord(
                                name=name,
                                line=record.line,
                                source="star-reexport",
                                confidence=init_export_confidence,
                                complete=True,
                                origin_module=record.target_module,
                                origin_symbol=name,
                                explicit=name in explicit_names,
                            ),
                        )
                else:
                    for symbol in sorted(target.symbols, key=lambda item: item.name):
                        if symbol.name.startswith("_"):
                            continue
                        _add_export_record(
                            info,
                            modules,
                            ExportRecord(
                                name=symbol.name,
                                line=record.line,
                                source="star-reexport",
                                confidence="low",
                                complete=False,
                                origin_module=record.target_module,
                                origin_symbol=symbol.name,
                                explicit=symbol.name in explicit_names,
                            ),
                        )
                continue
            if not record.imported_symbol:
                continue
            exported_name = record.alias or record.imported_symbol
            if explicit_complete and exported_name not in explicit_names:
                continue
            _add_export_record(
                info,
                modules,
                ExportRecord(
                    name=exported_name,
                    line=record.line,
                    source="direct-reexport",
                    confidence=init_export_confidence,
                    complete=explicit_complete,
                    origin_module=record.target_module,
                    origin_symbol=record.imported_symbol,
                    explicit=exported_name in explicit_names,
                ),
            )


def _known_init_export_confidence(configured: str, inherited: str) -> str:
    if CONFIDENCE_ORDER[configured] < CONFIDENCE_ORDER[inherited]:
        return configured
    return inherited


def _add_export_record(info: ModuleInfo, modules: dict[str, ModuleInfo], export: ExportRecord) -> None:
    key = (export.name, export.source, export.origin_module, export.origin_symbol)
    existing = {
        (item.name, item.source, item.origin_module, item.origin_symbol)
        for item in info.export_records
    }
    if key in existing:
        return
    info.exports.add(export.name)
    info.export_records.append(export)
    info.state.public_api = True
    origin = modules.get(export.origin_module or "")
    if origin and export.origin_symbol:
        for symbol in origin.symbols:
            if symbol.name == export.origin_symbol:
                symbol.public_api = True
                symbol.exported = True
                if CONFIDENCE_ORDER[export.confidence] > CONFIDENCE_ORDER[symbol.public_api_confidence]:
                    symbol.public_api_confidence = export.confidence
                if export.source == "star-reexport" and not export.complete:
                    symbol.dynamic_uncertain = True


def _apply_module_states(context: AnalysisContext) -> None:
    reachable = _reachable_modules(context.entry_modules, context.graph)
    dynamic_targets = {
        edge["to"] for edge in context.graph.edges if edge.get("dynamic")
    }
    for module_name, module in context.modules.items():
        module.state.reachable = module_name in reachable
        module.state.referenced = bool(context.graph.reverse.get(module_name))
        module.state.entrypoint_managed = module_name in context.entry_modules
        module.state.public_api = bool(module.export_records)
        module.state.framework_managed = bool(module.framework_hints)
        module.state.dynamic_uncertain = module.dynamic_import_hints > 0 or module_name in dynamic_targets
        for symbol in module.symbols:
            symbol.reachable = module.state.reachable
            symbol.dynamic_uncertain = symbol.dynamic_uncertain or module.state.dynamic_uncertain
            symbol.public_api = symbol.public_api or symbol.exported
            symbol.framework_managed = symbol.framework_managed
    for module_name, symbols in context.entrypoint_symbols.items():
        module = context.modules.get(module_name)
        if not module:
            continue
        for symbol in module.symbols:
            if symbol.name in symbols:
                symbol.entrypoint_managed = True


def _reachable_modules(entry_modules: tuple[str, ...], graph) -> set[str]:
    seen: set[str] = set()
    stack = [module for module in entry_modules if module in graph.modules]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        stack.extend(sorted(graph.adjacency.get(module, set()) - seen, reverse=True))
    return seen


def filter_result(
    result: dict[str, Any],
    min_confidence: str = "low",
    severity_threshold: str = "info",
) -> dict[str, Any]:
    min_c = CONFIDENCE_ORDER[min_confidence]
    min_s = SEVERITY_ORDER[severity_threshold]
    issues = [
        issue
        for issue in result["issues"]
        if CONFIDENCE_ORDER[issue["confidence"]] >= min_c
        and SEVERITY_ORDER[issue["severity"]] >= min_s
    ]
    clone = dict(result)
    clone["issues"] = issues
    clone["summary"] = summary_from_issue_dicts(issues, len(result["graphs"].get("duplicate_groups", [])))
    return clone


def _parse_error_issues(modules: dict[str, ModuleInfo]) -> list[Issue]:
    issues: list[Issue] = []
    for info in sorted(modules.values(), key=lambda item: item.path):
        if not info.parse_error:
            continue
        issues.append(
            Issue(
                rule="parse-error",
                severity="error",
                confidence="high",
                path=info.path,
                module=info.module,
                range=Range(
                    Position(info.parse_error_line, info.parse_error_column),
                    Position(info.parse_error_end_line, info.parse_error_end_column),
                ),
                message=f"Could not parse Python file: {info.parse_error}.",
                evidence={
                    "error": info.parse_error,
                    "line": info.parse_error_line,
                    "column": info.parse_error_column,
                    "end_line": info.parse_error_end_line,
                    "end_column": info.parse_error_end_column,
                },
                actions=[Action("fix-syntax", True, "Fix the syntax error before trusting downstream analysis.")],
            )
        )
    return issues


def _config_error_issues(config: PythonConfig) -> list[Issue]:
    issues: list[Issue] = []
    for diagnostic in config.config_errors:
        issues.append(
            Issue(
                rule="config-error",
                severity="error",
                confidence="high",
                path=relpath(config.config_path, config.root) if config.config_path else None,
                message=diagnostic["message"],
                evidence={"key": diagnostic["key"]},
                actions=[Action("fix-config", True, "Fix the invalid pyfallow configuration value.")],
            )
        )
    return issues


def _mark_entrypoint_symbols_used(issues: list[Issue], entrypoint_symbols: dict[str, set[str]]) -> None:
    if not entrypoint_symbols:
        return
    issues[:] = [
        issue
        for issue in issues
        if not (
            issue.rule == "unused-symbol"
            and issue.module in entrypoint_symbols
            and issue.symbol in entrypoint_symbols[issue.module]
        )
    ]


def _changed_only_reason(config: PythonConfig) -> str | None:
    if not config.changed_only_requested:
        return None
    if config.changed_only_effective:
        if config.since_ref:
            return f"diff-aware analysis was applied since {config.since_ref}"
        return "changed-only analysis was applied"
    if config.analysis_warnings:
        return config.analysis_warnings[-1]["message"]
    return "changed-only analysis was requested but full analysis was used"


def _diff_scope_default(config: PythonConfig) -> dict[str, Any]:
    return {
        "since": config.since_ref,
        "since_resolved": None,
        "changed_files": [],
        "changed_modules": [],
        "filtering_active": False,
        "reason": None,
    }


def _apply_diff_scope(
    config: PythonConfig,
    issues: list[Issue],
    modules: dict[str, ModuleInfo],
    duplicate_groups: list[dict[str, Any]],
    cycle_graphs: list[dict[str, Any]],
) -> tuple[list[Issue], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    config.changed_only_requested = True
    assert config.since_ref is not None
    resolution = resolve_since(config.root, config.since_ref, config.ignore)
    changed_files = set(resolution.changed_files)
    changed_modules = {
        module.module
        for module in modules.values()
        if module.path in changed_files
    }
    diff_scope = {
        "since": config.since_ref,
        "since_resolved": resolution.since_resolved,
        "changed_files": sorted(changed_files),
        "changed_modules": sorted(changed_modules),
        "filtering_active": resolution.filtering_active,
        "reason": None,
    }
    if resolution.warning:
        config.changed_only_effective = False
        warning = (
            _changed_only_alias_unavailable_warning(resolution.warning)
            if config.changed_only_alias
            else resolution.warning
        )
        config.analysis_warnings.append(warning)
        diff_scope["reason"] = warning["message"]
        return issues, duplicate_groups, cycle_graphs, diff_scope

    config.changed_only_effective = True
    if config.changed_only_alias:
        config.analysis_warnings.append(
            {
                "code": "changed-only-deprecated",
                "message": "--changed-only is deprecated; use --since HEAD~1 instead.",
            }
        )
    diff_scope["reason"] = f"Filtered findings to files changed since {config.since_ref}."
    filtered_issues = [
        issue
        for issue in issues
        if _issue_in_diff_scope(issue, changed_files, changed_modules)
    ]
    filtered_duplicate_groups = [
        group
        for group in duplicate_groups
        if any(fragment.get("path") in changed_files for fragment in group.get("fragments", []))
    ]
    filtered_cycle_graphs = [
        cycle
        for cycle in cycle_graphs
        if _cycle_graph_in_diff_scope(cycle, changed_files, changed_modules)
    ]
    return filtered_issues, filtered_duplicate_groups, filtered_cycle_graphs, diff_scope


def _changed_only_alias_unavailable_warning(warning: dict[str, str]) -> dict[str, str]:
    if warning["code"] != "since-not-available-non-git":
        return warning
    return {
        "code": "changed-only-not-available-non-git",
        "message": "--changed-only requested outside a Git workspace; full analysis was used. "
        "Use --since HEAD~1 in Git workspaces for diff-aware analysis.",
    }


def _issue_in_diff_scope(issue: Issue, changed_files: set[str], changed_modules: set[str]) -> bool:
    if issue.path and issue.path in changed_files:
        return True
    if issue.rule == "circular-dependency":
        cycle_path = set(issue.evidence.get("cycle_path", []))
        files = set(issue.evidence.get("files", []))
        return bool(cycle_path & changed_modules or files & changed_files)
    if issue.rule == "boundary-violation":
        evidence = issue.evidence
        modules = {evidence.get("importer_module"), evidence.get("imported_module")}
        paths = {evidence.get("importer_path"), evidence.get("imported_path")}
        matching_modules = {item for item in modules if item} & changed_modules
        matching_paths = {item for item in paths if item} & changed_files
        return bool(matching_modules or matching_paths)
    if issue.rule == "duplicate-code":
        return any(fragment.get("path") in changed_files for fragment in issue.evidence.get("fragments", []))
    return False


def _cycle_graph_in_diff_scope(
    cycle: dict[str, Any],
    changed_files: set[str],
    changed_modules: set[str],
) -> bool:
    return bool(set(cycle.get("modules", [])) & changed_modules or set(cycle.get("files", [])) & changed_files)


def _import_issues(records: list[ImportRecord]) -> list[Issue]:
    issues: list[Issue] = []
    for record in sorted(records, key=lambda item: (item.path, item.line, item.raw_module or "")):
        if record.dynamic and not record.dynamic_literal:
            issues.append(
                Issue(
                    rule="dynamic-import",
                    severity="info",
                    confidence="low",
                    path=record.path,
                    module=record.importer,
                    range=Range(Position(record.line, record.column + 1), Position(record.line, record.column + 1)),
                    message="Dynamic import target is not a string literal and cannot be resolved statically.",
                    evidence={"importer": record.importer, "reason": "Non-literal importlib/__import__ target."},
                    actions=[Action("review-dynamic-import", False, "Add explicit config or keep confidence low for dependent findings.")],
                )
            )
        if record.level and record.classification == "unresolved":
            issues.append(
                Issue(
                    rule="unresolved-import",
                    severity="warning",
                    confidence="medium",
                    path=record.path,
                    module=record.importer,
                    range=Range(Position(record.line, record.column + 1), Position(record.line, record.column + 1)),
                    message="Relative import could not be resolved to a discovered module.",
                    evidence={
                        "raw_module": record.raw_module,
                        "imported_symbol": record.imported_symbol,
                        "level": record.level,
                    },
                    actions=[Action("review-import", False, "Check source roots, namespace package settings, or the import target.")],
                )
            )
    return issues


def _production_test_import_issues(
    config: PythonConfig,
    records: list[ImportRecord],
    modules: dict[str, ModuleInfo],
) -> list[Issue]:
    if config.include_tests:
        return []
    issues: list[Issue] = []
    seen: set[tuple[str, str, int]] = set()
    for record in sorted(records, key=lambda item: (item.path, item.line, item.raw_module or "", item.imported_symbol or "")):
        if record.classification != "local" or not record.target_module:
            continue
        importer = modules.get(record.importer)
        target = modules.get(record.target_module)
        if not importer or not target or importer.is_test or not target.is_test:
            continue
        key = (record.importer, record.target_module, record.line)
        if key in seen:
            continue
        seen.add(key)
        issues.append(
            Issue(
                rule="production-imports-test-code",
                severity="warning",
                confidence="high",
                path=record.path,
                module=record.importer,
                range=Range(Position(record.line, record.column + 1), Position(record.line, record.column + 1)),
                message=f"Production module '{record.importer}' imports test module '{record.target_module}'.",
                evidence={
                    "importer": record.importer,
                    "importer_path": importer.path,
                    "target_module": record.target_module,
                    "target_path": target.path,
                    "reason": "include_tests=false excludes test edges from production analysis; importing tests from production is still reported.",
                },
                actions=[
                    Action(
                        "move-test-helper",
                        False,
                        "Move shared helpers out of tests or remove the production dependency on test code.",
                    )
                ],
            )
        )
    return issues


def _cycle_issues(
    components: list[list[str]],
    graph,
    modules: dict[str, ModuleInfo],
) -> tuple[list[Issue], list[dict[str, Any]], set[str]]:
    issues: list[Issue] = []
    graphs: list[dict[str, Any]] = []
    cycle_modules: set[str] = set()
    for component in components:
        path = cycle_path(component, graph)
        cycle_modules.update(component)
        import_lines = []
        files = []
        for source, target in zip(path, path[1:]):
            edge = edge_for(graph, source, target)
            if edge:
                import_lines.append({"from": source, "to": target, "path": edge["path"], "line": edge["line"]})
                files.append(edge["path"])
        files = sorted(set(files))
        graphs.append({"modules": component, "path": path, "files": files, "import_lines": import_lines})
        first_file = files[0] if files else modules[component[0]].path
        first_line = import_lines[0]["line"] if import_lines else 1
        type_checking = any(
            edge["type_checking"]
            for source, target in zip(path, path[1:])
            for edge in graph.edges
            if edge["from"] == source and edge["to"] == target
        )
        issues.append(
            Issue(
                rule="circular-dependency",
                severity="warning",
                confidence="high",
                path=first_file,
                module=component[0],
                range=Range(Position(first_line, 1), Position(first_line, 1)),
                message="Import cycle detected: " + " -> ".join(path),
                evidence={
                    "cycle_path": path,
                    "files": files,
                    "import_lines": import_lines,
                    "type_checking_imports_contributed": type_checking,
                    "suggested_remediation": [
                        "extract shared interface/module",
                        "invert dependency",
                        "split module responsibilities",
                        "use TYPE_CHECKING only if the cycle is type-hint-only",
                    ],
                },
                actions=[
                    Action("break-cycle", False, "Extract a shared abstraction or invert one dependency edge."),
                    Action("move-type-import", False, "Use TYPE_CHECKING only when the cycle is purely type-hint related."),
                ],
            )
        )
    return issues, graphs, cycle_modules


def _summary(issues: list[Issue], duplicate_groups: list[dict[str, Any]]) -> dict[str, int]:
    return summary_from_issue_dicts([issue.to_dict() for issue in issues], len(duplicate_groups))


def _issue_sort_key(issue: Issue) -> tuple[Any, ...]:
    return (
        -SEVERITY_ORDER[issue.severity],
        RULES[issue.rule]["id"],
        issue.path or "",
        issue.range.start.line,
        issue.symbol or "",
        issue.message,
    )
