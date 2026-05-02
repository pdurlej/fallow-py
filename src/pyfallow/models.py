from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VERSION = "0.1.0-alpha.1"
SCHEMA_VERSION = "1.0"


RULES: dict[str, dict[str, str]] = {
    "parse-error": {"id": "PY000", "category": "parser", "default_severity": "error"},
    "config-error": {"id": "PY001", "category": "config", "default_severity": "error"},
    "unresolved-import": {"id": "PY010", "category": "imports", "default_severity": "warning"},
    "dynamic-import": {"id": "PY011", "category": "imports", "default_severity": "info"},
    "production-imports-test-code": {"id": "PY012", "category": "imports", "default_severity": "warning"},
    "circular-dependency": {"id": "PY020", "category": "architecture", "default_severity": "warning"},
    "unused-module": {"id": "PY030", "category": "dead-code", "default_severity": "warning"},
    "unused-symbol": {"id": "PY031", "category": "dead-code", "default_severity": "info"},
    "stale-suppression": {"id": "PY032", "category": "suppressions", "default_severity": "info"},
    "missing-runtime-dependency": {"id": "PY040", "category": "dependencies", "default_severity": "error"},
    "missing-type-dependency": {"id": "PY043", "category": "dependencies", "default_severity": "info"},
    "missing-test-dependency": {"id": "PY044", "category": "dependencies", "default_severity": "info"},
    "dev-dependency-used-in-runtime": {"id": "PY045", "category": "dependencies", "default_severity": "error"},
    "optional-dependency-used-in-runtime": {
        "id": "PY046",
        "category": "dependencies",
        "default_severity": "warning",
    },
    "runtime-dependency-used-only-in-tests": {
        "id": "PY047",
        "category": "dependencies",
        "default_severity": "warning",
    },
    "runtime-dependency-used-only-for-types": {
        "id": "PY048",
        "category": "dependencies",
        "default_severity": "info",
    },
    "unused-runtime-dependency": {"id": "PY049", "category": "dependencies", "default_severity": "warning"},
    "duplicate-code": {"id": "PY050", "category": "duplication", "default_severity": "warning"},
    "high-cyclomatic-complexity": {
        "id": "PY060",
        "category": "health",
        "default_severity": "warning",
    },
    "high-cognitive-complexity": {
        "id": "PY061",
        "category": "health",
        "default_severity": "warning",
    },
    "large-function": {"id": "PY062", "category": "health", "default_severity": "info"},
    "large-file": {"id": "PY063", "category": "health", "default_severity": "info"},
    "boundary-violation": {
        "id": "PY070",
        "category": "architecture",
        "default_severity": "warning",
    },
    "framework-entrypoint-detected": {
        "id": "PY080",
        "category": "frameworks",
        "default_severity": "info",
    },
    "risky-hotspot": {"id": "PY090", "category": "health", "default_severity": "warning"},
}

for _rule in RULES.values():
    _rule.setdefault(
        "precision",
        {"error": "very-high", "warning": "high", "info": "medium"}[_rule["default_severity"]],
    )

SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass(slots=True)
class Position:
    line: int = 1
    column: int = 1

    def to_dict(self) -> dict[str, int]:
        return {"line": self.line, "column": self.column}


@dataclass(slots=True)
class Range:
    start: Position = field(default_factory=Position)
    end: Position = field(default_factory=Position)

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}


@dataclass(slots=True)
class Action:
    type: str
    safe: bool
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "safe": self.safe, "description": self.description}


@dataclass(slots=True)
class Issue:
    rule: str
    severity: str
    confidence: str
    path: str | None
    message: str
    range: Range = field(default_factory=Range)
    symbol: str | None = None
    module: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    actions: list[Action] = field(default_factory=list)
    fingerprint: str = ""

    @property
    def id(self) -> str:
        return RULES[self.rule]["id"]

    @property
    def category(self) -> str:
        return RULES[self.rule]["category"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule": self.rule,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "path": self.path,
            "range": self.range.to_dict(),
            "symbol": self.symbol,
            "module": self.module,
            "message": self.message,
            "evidence": stable_data(self.evidence),
            "actions": [action.to_dict() for action in self.actions],
            "fingerprint": self.fingerprint,
        }


@dataclass(slots=True)
class ImportRecord:
    importer: str
    path: str
    raw_module: str | None
    imported_symbol: str | None
    alias: str | None
    level: int
    line: int
    column: int
    kind: str
    in_function: bool = False
    type_checking: bool = False
    guarded: bool = False
    dynamic: bool = False
    dynamic_literal: bool = True
    target_module: str | None = None
    target_path: str | None = None
    classification: str = "unresolved"
    distribution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "importer": self.importer,
            "path": self.path,
            "raw_module": self.raw_module,
            "imported_symbol": self.imported_symbol,
            "alias": self.alias,
            "level": self.level,
            "line": self.line,
            "column": self.column + 1,
            "kind": self.kind,
            "in_function": self.in_function,
            "type_checking": self.type_checking,
            "guarded": self.guarded,
            "dynamic": self.dynamic,
            "dynamic_literal": self.dynamic_literal,
            "target_module": self.target_module,
            "target_path": self.target_path,
            "classification": self.classification,
            "distribution": self.distribution,
        }


@dataclass(slots=True)
class SymbolRecord:
    name: str
    kind: str
    line: int
    column: int
    end_line: int
    end_column: int
    bases: list[str] = field(default_factory=list)
    decorated: bool = False
    framework_managed: bool = False
    exported: bool = False
    reachable: bool = False
    referenced: bool = False
    public_api: bool = False
    public_api_confidence: str = "low"
    entrypoint_managed: bool = False
    dynamic_uncertain: bool = False
    referenced_by_production: int = 0
    referenced_by_tests: int = 0
    referenced_by_type_only: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "line": self.line,
            "column": self.column + 1,
            "end_line": self.end_line,
            "end_column": self.end_column + 1,
            "bases": list(self.bases),
            "decorated": self.decorated,
            "framework_managed": self.framework_managed,
            "exported": self.public_api or self.exported,
            "state": {
                "reachable": self.reachable,
                "referenced": self.referenced,
                "public_api": self.public_api or self.exported,
                "public_api_confidence": self.public_api_confidence,
                "framework_managed": self.framework_managed,
                "entrypoint_managed": self.entrypoint_managed,
                "dynamic_uncertain": self.dynamic_uncertain,
                "referenced_by": {
                    "production": self.referenced_by_production,
                    "tests": self.referenced_by_tests,
                    "type_only": self.referenced_by_type_only,
                },
            },
        }


@dataclass(slots=True)
class ExportRecord:
    name: str
    line: int
    source: str
    confidence: str
    complete: bool
    origin_module: str | None = None
    origin_symbol: str | None = None
    explicit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "line": self.line,
            "source": self.source,
            "confidence": self.confidence,
            "complete": self.complete,
            "origin_module": self.origin_module,
            "origin_symbol": self.origin_symbol,
            "explicit": self.explicit,
        }


@dataclass(slots=True)
class Suppression:
    path: str
    line: int
    rule: str | None
    raw: str
    file_wide: bool = False
    used: bool = False

    def applies_to(self, issue: Issue) -> bool:
        if self.path != issue.path:
            return False
        if self.rule and self.rule != issue.rule:
            return False
        return self.file_wide or self.line == issue.range.start.line


@dataclass(slots=True)
class ModuleState:
    reachable: bool = False
    referenced: bool = False
    public_api: bool = False
    framework_managed: bool = False
    entrypoint_managed: bool = False
    dynamic_uncertain: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "reachable": self.reachable,
            "referenced": self.referenced,
            "public_api": self.public_api,
            "framework_managed": self.framework_managed,
            "entrypoint_managed": self.entrypoint_managed,
            "dynamic_uncertain": self.dynamic_uncertain,
        }


@dataclass(slots=True)
class FunctionInfo:
    name: str
    kind: str
    line: int
    column: int
    end_line: int
    end_column: int
    decorators: list[str] = field(default_factory=list)
    framework_managed: bool = False
    ast_node: Any = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "decorators": list(self.decorators),
            "framework_managed": self.framework_managed,
        }


@dataclass(slots=True)
class ModuleInfo:
    path: str
    module: str
    source_root: str
    is_package_init: bool
    is_test: bool
    is_migration: bool
    is_generated: bool
    imports: list[ImportRecord] = field(default_factory=list)
    symbols: list[SymbolRecord] = field(default_factory=list)
    name_refs: set[str] = field(default_factory=set)
    attribute_refs: list[tuple[str, str, int]] = field(default_factory=list)
    alias_to_module: dict[str, str] = field(default_factory=dict)
    alias_to_symbol: dict[str, tuple[str, str]] = field(default_factory=dict)
    exports: set[str] = field(default_factory=set)
    export_records: list[ExportRecord] = field(default_factory=list)
    suppressions: list[Suppression] = field(default_factory=list)
    dynamic_import_hints: int = 0
    framework_hints: set[str] = field(default_factory=set)
    parse_error: str | None = None
    parse_error_line: int = 1
    parse_error_column: int = 1
    parse_error_end_line: int = 1
    parse_error_end_column: int = 1
    line_count: int = 0
    functions: list[FunctionInfo] = field(default_factory=list)
    state: ModuleState = field(default_factory=ModuleState)

    def to_graph_node(self) -> dict[str, Any]:
        return {
            "id": self.module,
            "path": self.path,
            "is_package_init": self.is_package_init,
            "is_test": self.is_test,
            "is_migration": self.is_migration,
            "state": self.state.to_dict(),
            "exports": [record.to_dict() for record in sorted(self.export_records, key=lambda item: (item.name, item.line, item.source))],
            "symbols": [symbol.to_dict() for symbol in sorted(self.symbols, key=lambda item: (item.line, item.name))],
        }


def stable_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: stable_data(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [stable_data(item) for item in value]
    if isinstance(value, tuple):
        return [stable_data(item) for item in value]
    if isinstance(value, set):
        return [stable_data(item) for item in sorted(value)]
    return value
