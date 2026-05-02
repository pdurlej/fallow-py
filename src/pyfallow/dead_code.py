from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from .config import PythonConfig
from .graph import ImportGraph, reachable_from
from .models import CONFIDENCE_ORDER, Action, Issue, ModuleInfo, Position, Range

CONVENTIONAL_ENTRY_NAMES = {
    "__main__.py",
    "main.py",
    "app.py",
    "manage.py",
    "asgi.py",
    "wsgi.py",
    "server.py",
    "cli.py",
    "worker.py",
}

FRAMEWORK_SAFE_MODULE_NAMES = {
    "settings",
    "config",
    "urls",
    "admin",
    "apps",
    "models",
    "schemas",
    "serializers",
    "views",
    "tasks",
    "conftest",
}


def detect_entrypoints(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
    packaging_entrypoints: list[str],
) -> tuple[list[dict[str, Any]], list[str], bool, dict[str, set[str]]]:
    entries: list[dict[str, Any]] = []
    entry_symbols: dict[str, set[str]] = {}
    explicit = bool(config.entry)
    by_module = {module.module: module for module in modules.values()}
    for package_target in packaging_entrypoints:
        module_name, _, symbol_name = package_target.partition(":")
        if module_name in by_module:
            entries.append(_entry(by_module[module_name], "packaging-script", "high"))
            if symbol_name:
                entry_symbols.setdefault(module_name, set()).add(symbol_name)
        elif module_name.rsplit(".", 1)[0] in by_module:
            fallback_module = module_name.rsplit(".", 1)[0]
            entries.append(_entry(by_module[fallback_module], "packaging-script", "high"))
            entry_symbols.setdefault(fallback_module, set()).add(module_name.rsplit(".", 1)[-1])
    if explicit:
        for pattern in config.entry:
            for module in sorted(modules.values(), key=lambda item: item.path):
                if fnmatch(module.path, pattern):
                    entries.append(_entry(module, "explicit-config", "high"))
                    for symbol in _entrypoint_function_names(config, module):
                        entry_symbols.setdefault(module.module, set()).add(symbol)
    else:
        for module in sorted(modules.values(), key=lambda item: item.path):
            name = module.path.rsplit("/", 1)[-1]
            if name in CONVENTIONAL_ENTRY_NAMES:
                entries.append(_entry(module, "conventional-name", "medium"))
                for symbol in _entrypoint_function_names(config, module):
                    entry_symbols.setdefault(module.module, set()).add(symbol)
            elif config.include_tests and name == "conftest.py":
                entries.append(_entry(module, "pytest-conftest", "medium"))
            elif _framework_entry(module):
                entries.append(_entry(module, "framework-heuristic", "low"))
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for entry in entries:
        if entry["module"] not in seen:
            seen.add(entry["module"])
            deduped.append(entry)
    return deduped, [entry["module"] for entry in deduped], explicit, entry_symbols


def dead_code_issues(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
    graph: ImportGraph,
    entry_modules: list[str],
    explicit_entrypoints: bool,
) -> list[Issue]:
    if not config.dead_code.enabled:
        return []
    issues: list[Issue] = []
    reachable = reachable_from(entry_modules, graph)
    if config.dead_code.detect_unused_modules:
        issues.extend(_unused_module_issues(config, modules, graph, reachable, entry_modules, explicit_entrypoints))
    if config.dead_code.detect_unused_symbols:
        issues.extend(_unused_symbol_issues(config, modules, graph))
    return issues


def _unused_module_issues(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
    graph: ImportGraph,
    reachable: set[str],
    entry_modules: list[str],
    explicit_entrypoints: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    if not entry_modules:
        return issues
    for module in sorted(modules.values(), key=lambda item: item.path):
        if module.module in reachable:
            continue
        if module.parse_error:
            continue
        if module.is_test and not config.include_tests:
            continue
        if module.is_package_init and config.dead_code.treat_init_as_entry:
            continue
        if module.is_migration or module.is_generated:
            continue
        if "/management/commands/" in f"/{module.path}":
            continue
        confidence = "high" if explicit_entrypoints else "medium"
        reason = "No inbound local import path from any entrypoint."
        basename = module.module.rsplit(".", 1)[-1]
        if module.dynamic_import_hints or basename in FRAMEWORK_SAFE_MODULE_NAMES or module.framework_hints:
            confidence = "low"
            reason = "Unreachable statically, but framework or dynamic-import uncertainty lowers confidence."
        imported_by = sorted(graph.reverse.get(module.module, set()))
        issues.append(
            Issue(
                rule="unused-module",
                severity="warning",
                confidence=confidence,
                path=module.path,
                module=module.module,
                range=Range(Position(1, 1), Position(1, 1)),
                message="Module is not reachable from configured or inferred entry points.",
                evidence={
                    "entrypoints": sorted(entry_modules),
                    "imported_by": imported_by,
                    "imports": sorted(graph.adjacency.get(module.module, set())),
                    "reason": reason,
                },
                actions=[
                    Action(
                        "review-delete-file",
                        False,
                        "Review manually before deleting; dynamic imports or framework loading may still reference this module.",
                    )
                ],
            )
        )
    return issues


def _unused_symbol_issues(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
    graph: ImportGraph,
) -> list[Issue]:
    references = _collect_symbol_references(config, modules)
    _propagate_export_usage(modules, references)
    _apply_symbol_reference_states(config, modules, references)

    for module in modules.values():
        if module.parse_error:
            continue

    issues: list[Issue] = []
    ignored_symbols = set(config.dead_code.ignore_symbols)
    for module in sorted(modules.values(), key=lambda item: item.path):
        if module.parse_error or (module.is_test and not config.include_tests):
            continue
        for symbol in sorted(module.symbols, key=lambda item: (item.line, item.name)):
            if _skip_symbol(config, module, symbol, ignored_symbols):
                continue
            counts = references.get(module.module, {}).get(symbol.name, {})
            if _referenced_in_active_scope(config, counts):
                continue
            confidence = "low" if symbol.kind == "assignment" or symbol.decorated else "medium"
            reason = "No static reference, import, or high-confidence public export was found."
            if symbol.public_api and CONFIDENCE_ORDER[symbol.public_api_confidence] == CONFIDENCE_ORDER["low"]:
                confidence = "low"
                reason = "Symbol is only exposed through a low-confidence public API path; dynamic uncertainty prevents treating it as used."
            elif counts.get("type_only", 0):
                confidence = "low"
                reason = "Symbol is referenced only under TYPE_CHECKING, not by production runtime code."
            elif counts.get("tests", 0) and not config.include_tests:
                confidence = "low"
                reason = "Symbol is referenced only by tests, and include_tests=false keeps test usage separate."
            severity = "warning" if confidence == "medium" else "info"
            issues.append(
                Issue(
                    rule="unused-symbol",
                    severity=severity,
                    confidence=confidence,
                    path=module.path,
                    module=module.module,
                    symbol=symbol.name,
                    range=Range(
                        Position(symbol.line, symbol.column + 1),
                        Position(symbol.end_line, symbol.end_column + 1),
                    ),
                    message=f"Top-level {symbol.kind} '{symbol.name}' is not referenced by analyzed modules.",
                    evidence={
                        "module": module.module,
                        "kind": symbol.kind,
                        "exported": symbol.exported,
                        "public_api": symbol.public_api,
                        "public_api_confidence": symbol.public_api_confidence,
                        "framework_managed": symbol.framework_managed,
                        "entrypoint_managed": symbol.entrypoint_managed,
                        "state": symbol.to_dict()["state"],
                        "reason": reason,
                    },
                    actions=[
                        Action(
                            "review-remove-symbol",
                            False,
                            "Review callers, framework hooks, and dynamic access before removing.",
                        )
                    ],
                )
            )
    return issues


def _skip_symbol(
    config: PythonConfig,
    module: ModuleInfo,
    symbol,
    ignored_symbols: set[str],
) -> bool:
    if symbol.name in ignored_symbols:
        return True
    if symbol.name.startswith("_"):
        return True
    if symbol.name.startswith("__") and symbol.name.endswith("__"):
        return True
    if (symbol.public_api or symbol.exported) and CONFIDENCE_ORDER[symbol.public_api_confidence] >= CONFIDENCE_ORDER["medium"]:
        return True
    if symbol.framework_managed:
        return True
    if config.dead_code.ignore_decorated and symbol.decorated:
        return True
    if module.is_package_init:
        return True
    if module.framework_hints and symbol.kind == "assignment":
        return True
    if symbol.entrypoint_managed:
        return True
    return False


def _local_prefix(module: str, modules: dict[str, ModuleInfo]) -> str | None:
    parts = module.split(".")
    for index in range(len(parts), 0, -1):
        candidate = ".".join(parts[:index])
        if candidate in modules:
            return candidate
    return None


def _entry(module: ModuleInfo, reason: str, confidence: str) -> dict[str, Any]:
    return {"path": module.path, "module": module.module, "reason": reason, "confidence": confidence}


def _framework_entry(module: ModuleInfo) -> bool:
    basename = Path(module.path).name
    return bool(module.framework_hints and basename in {"app.py", "main.py", "server.py", "worker.py"})


def _entrypoint_function_names(config: PythonConfig, module: ModuleInfo) -> set[str]:
    conventional = set(config.dead_code.entry_symbols)
    return {symbol.name for symbol in module.symbols if symbol.kind in {"function", "async-function"} and symbol.name in conventional}


def _collect_symbol_references(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
) -> dict[str, dict[str, dict[str, int]]]:
    references: dict[str, dict[str, dict[str, int]]] = {name: {} for name in modules}
    reexport_imports = _reexport_imports(modules)
    for module in sorted(modules.values(), key=lambda item: item.module):
        if module.parse_error:
            continue
        scope = "tests" if module.is_test else "production"
        for name in module.name_refs:
            _add_reference(references, module.module, name, scope)
        for base, attr, _line in module.attribute_refs:
            if base in module.alias_to_module:
                target_module = _local_prefix(module.alias_to_module[base], modules)
                if target_module:
                    _add_reference(references, target_module, attr, scope)
            if base in module.alias_to_symbol:
                target_module, symbol = module.alias_to_symbol[base]
                local = _local_prefix(target_module, modules)
                if local:
                    _add_reference(references, local, symbol, scope)
        for record in module.imports:
            if record.classification != "local" or not record.target_module or not record.imported_symbol:
                continue
            if (module.module, record.target_module, record.imported_symbol) in reexport_imports:
                continue
            target_scope = "type_only" if record.type_checking else scope
            _add_reference(references, record.target_module, record.imported_symbol, target_scope)
    return references


def _reexport_imports(modules: dict[str, ModuleInfo]) -> set[tuple[str, str, str]]:
    result: set[tuple[str, str, str]] = set()
    for module in modules.values():
        if not module.is_package_init:
            continue
        for export in module.export_records:
            if export.origin_module and export.origin_symbol and export.source == "direct-reexport":
                result.add((module.module, export.origin_module, export.origin_symbol))
    return result


def _add_reference(
    references: dict[str, dict[str, dict[str, int]]],
    module: str,
    symbol: str,
    scope: str,
) -> None:
    counts = references.setdefault(module, {}).setdefault(
        symbol,
        {"production": 0, "tests": 0, "type_only": 0},
    )
    counts[scope] += 1


def _referenced_in_active_scope(config: PythonConfig, counts: dict[str, int]) -> bool:
    if counts.get("production", 0) > 0:
        return True
    if config.include_tests and counts.get("tests", 0) > 0:
        return True
    return False


def _propagate_export_usage(
    modules: dict[str, ModuleInfo],
    references: dict[str, dict[str, dict[str, int]]],
) -> None:
    for package in sorted(modules.values(), key=lambda item: item.module):
        if not package.export_records:
            continue
        for export in package.export_records:
            if not export.origin_module or not export.origin_symbol:
                continue
            counts = references.get(package.module, {}).get(export.name)
            if not counts:
                continue
            for scope, count in counts.items():
                for _ in range(count):
                    _add_reference(references, export.origin_module, export.origin_symbol, scope)


def _apply_symbol_reference_states(
    config: PythonConfig,
    modules: dict[str, ModuleInfo],
    references: dict[str, dict[str, dict[str, int]]],
) -> None:
    for module_name, names in references.items():
        module = modules.get(module_name)
        if not module:
            continue
        for symbol in module.symbols:
            counts = names.get(symbol.name, {})
            symbol.referenced_by_production = counts.get("production", 0)
            symbol.referenced_by_tests = counts.get("tests", 0)
            symbol.referenced_by_type_only = counts.get("type_only", 0)
            symbol.referenced = _referenced_in_active_scope(config, counts)
