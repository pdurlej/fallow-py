from __future__ import annotations

import configparser
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import PythonConfig
from .models import Action, ImportRecord, Issue, Position, Range
from .paths import normalize_package_name, relpath

REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
SCRIPT_TARGET_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*:")


@dataclass(slots=True)
class DependencyDeclarations:
    runtime: dict[str, str] = field(default_factory=dict)
    optional: dict[str, str] = field(default_factory=dict)
    dev: dict[str, str] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    script_targets: list[tuple[str, str]] = field(default_factory=list)

    @property
    def all(self) -> dict[str, str]:
        merged = {}
        merged.update(self.runtime)
        merged.update(self.optional)
        merged.update(self.dev)
        return merged


def parse_dependency_declarations(root: Path) -> DependencyDeclarations:
    declarations = DependencyDeclarations()
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        _parse_pyproject(pyproject, root, declarations)
    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        _parse_setup_cfg(setup_cfg, root, declarations)
    for req in sorted([root / "requirements.txt", *list((root / "requirements").glob("*.txt") if (root / "requirements").is_dir() else [])]):
        if req.exists():
            declarations.files.append(relpath(req, root))
            for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
                name = _requirement_name(line)
                if name:
                    declarations.runtime.setdefault(name, relpath(req, root))
    return declarations


def classify_imports(records: list[ImportRecord], config: PythonConfig) -> None:
    stdlib = set(getattr(sys, "stdlib_module_names", set())) | FALLBACK_STDLIB
    import_map = config.dependencies.import_map
    normalized_map = {key: normalize_package_name(value) for key, value in import_map.items()}
    sorted_keys = sorted(normalized_map, key=lambda item: len(item), reverse=True)
    for record in records:
        if record.classification == "local":
            continue
        if record.dynamic and not record.dynamic_literal:
            record.classification = "dynamic"
            continue
        module = record.raw_module or ""
        if not module:
            record.classification = "unresolved"
            continue
        top = module.split(".", 1)[0]
        if top in stdlib:
            record.classification = "stdlib"
            continue
        record.classification = "third-party"
        distribution = None
        for key in sorted_keys:
            if module == key or module.startswith(key + ".") or top == key:
                distribution = normalized_map[key]
                break
        record.distribution = distribution or normalize_package_name(top)


def dependency_issues(
    config: PythonConfig,
    declarations: DependencyDeclarations,
    records: list[ImportRecord],
) -> list[Issue]:
    if not config.dependencies.enabled:
        return []
    issues: list[Issue] = []
    ignored = {normalize_package_name(item) for item in config.dependencies.ignore}
    runtime = {normalize_package_name(name): source for name, source in declarations.runtime.items()}
    optional = {normalize_package_name(name): source for name, source in declarations.optional.items()}
    dev = {normalize_package_name(name): source for name, source in declarations.dev.items()}
    used: dict[str, list[ImportRecord]] = {}
    for record in records:
        if record.classification != "third-party" or not record.distribution:
            continue
        used.setdefault(record.distribution, []).append(record)

    if config.dependencies.check_missing:
        for dist, import_records in sorted(used.items()):
            if dist in ignored:
                continue
            in_runtime = dist in runtime
            in_optional = dist in optional
            in_dev = dist in dev
            policy = _dependency_policy(import_records)
            production_uses = [
                record
                for record in import_records
                if not _is_test_path(record.path) and not record.type_checking and not record.guarded
            ]
            first = sorted(import_records, key=lambda item: (item.path, item.line))[0]
            if not in_runtime and not in_optional and not in_dev:
                if policy == "test-only" and not config.dependencies.report_test_only_missing:
                    continue
                rule = "missing-runtime-dependency"
                severity = "error"
                confidence = "high" if not first.guarded else "medium"
                action = Action(
                    "declare-dependency",
                    False,
                    f"Add '{dist}' to project dependencies if it is required at runtime.",
                )
                if policy == "type-only":
                    if not config.dependencies.report_type_only_missing:
                        continue
                    rule = "missing-type-dependency"
                    severity = "info"
                    confidence = "low"
                    action = Action(
                        "review-type-dependency",
                        False,
                        f"Declare '{dist}' in an appropriate typing/dev dependency group if type checking requires it.",
                    )
                elif policy == "test-only":
                    rule = "missing-test-dependency"
                    severity = "info"
                    confidence = "low"
                    action = Action(
                        "review-test-dependency",
                        False,
                        f"Declare '{dist}' in a test/dev dependency group if tests require it.",
                    )
                issues.append(
                    Issue(
                        rule=rule,
                        severity=severity,
                        confidence=confidence,
                        path=first.path,
                        range=Range(Position(first.line, first.column + 1), Position(first.line, first.column + 1)),
                        message=f"Imported third-party package '{dist}' is not declared as a dependency.",
                        evidence={
                            "distribution": dist,
                            "imports": [_import_location(record) for record in import_records[:10]],
                            "mapping": first.raw_module,
                            "guarded": any(record.guarded for record in import_records),
                            "type_checking_only": policy == "type-only",
                            "policy": policy,
                            "legacy_rule": "missing-dependency",
                        },
                        actions=[action],
                    )
                )
            elif in_dev and production_uses and not in_runtime:
                issues.append(
                    Issue(
                        rule="dev-dependency-used-in-runtime",
                        severity="error",
                        confidence="medium",
                        path=production_uses[0].path,
                        range=Range(
                            Position(production_uses[0].line, production_uses[0].column + 1),
                            Position(production_uses[0].line, production_uses[0].column + 1),
                        ),
                        message=f"Package '{dist}' is declared only for development but used by production code.",
                        evidence={
                            "distribution": dist,
                            "declared_in": dev[dist],
                            "imports": [_import_location(record) for record in production_uses[:10]],
                            "policy": "dev-declared-runtime-use",
                            "legacy_rule": "missing-dependency",
                        },
                        actions=[
                            Action(
                                "move-dependency",
                                False,
                                f"Move '{dist}' to runtime dependencies or isolate the import to tests/dev tooling.",
                            )
                        ],
                    )
                )
            elif in_optional and production_uses and not in_runtime:
                issues.append(
                    Issue(
                        rule="optional-dependency-used-in-runtime",
                        severity="warning",
                        confidence="medium",
                        path=production_uses[0].path,
                        range=Range(
                            Position(production_uses[0].line, production_uses[0].column + 1),
                            Position(production_uses[0].line, production_uses[0].column + 1),
                        ),
                        message=f"Optional dependency '{dist}' is imported by production code.",
                        evidence={
                            "distribution": dist,
                            "declared_in": optional[dist],
                            "imports": [_import_location(record) for record in production_uses[:10]],
                            "policy": "optional-declared-runtime-use",
                            "legacy_rule": "undeclared-optional-dependency",
                        },
                        actions=[
                            Action(
                                "review-optional-dependency",
                                False,
                                "Guard the import or promote the dependency if the code path is required.",
                            )
                        ],
                    )
                )

    if config.dependencies.check_unused:
        for dist, source in sorted(runtime.items()):
            if dist in ignored:
                continue
            if dist in used:
                policy = _dependency_policy(used[dist])
                if policy in {"test-only", "type-only"}:
                    first = sorted(used[dist], key=lambda item: (item.path, item.line))[0]
                    issues.append(
                        Issue(
                            rule=(
                                "runtime-dependency-used-only-in-tests"
                                if policy == "test-only"
                                else "runtime-dependency-used-only-for-types"
                            ),
                            severity="warning" if policy == "test-only" else "info",
                            confidence="medium" if policy == "test-only" else "low",
                            path=source,
                            message=(
                                f"Runtime dependency '{dist}' is imported only from tests."
                                if policy == "test-only"
                                else f"Runtime dependency '{dist}' is imported only under TYPE_CHECKING."
                            ),
                            evidence={
                                "distribution": dist,
                                "declared_in": source,
                                "imports": [_import_location(record) for record in used[dist][:10]],
                                "policy": policy,
                                "first_import": _import_location(first),
                                "legacy_rule": "unused-dependency",
                            },
                            actions=[
                                Action(
                                    "review-dependency-scope",
                                    False,
                                    "Move the dependency to a narrower dev/type group if runtime code does not need it.",
                                )
                            ],
                        )
                    )
                continue
            issues.append(
                Issue(
                    rule="unused-runtime-dependency",
                    severity="warning",
                    confidence="medium",
                    path=source,
                    message=f"Declared dependency '{dist}' was not imported by analyzed Python code.",
                    evidence={
                        "distribution": dist,
                        "declared_in": source,
                        "reason": "No static import matched this distribution.",
                        "policy": "unused-runtime",
                        "legacy_rule": "unused-dependency",
                    },
                    actions=[
                        Action(
                            "review-remove-dependency",
                            False,
                            "Review runtime usage, plugin loading, and packaging metadata before removing.",
                        )
                    ],
                )
            )
    return issues


def entrypoints_from_packaging(declarations: DependencyDeclarations) -> list[str]:
    return sorted(f"{module}:{symbol}" for module, symbol in declarations.script_targets)


def _parse_pyproject(path: Path, root: Path, declarations: DependencyDeclarations) -> None:
    declarations.files.append(relpath(path, root))
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    for dep in project.get("dependencies", []):
        name = _requirement_name(str(dep))
        if name:
            declarations.runtime.setdefault(name, relpath(path, root))
    for deps in project.get("optional-dependencies", {}).values():
        for dep in deps:
            name = _requirement_name(str(dep))
            if name:
                declarations.optional.setdefault(name, relpath(path, root))
    for target in project.get("scripts", {}).values():
        match = SCRIPT_TARGET_RE.match(str(target))
        if match:
            _add_script_target(declarations, str(target), match.group(1))

    poetry = data.get("tool", {}).get("poetry", {})
    for dep in poetry.get("dependencies", {}):
        if dep.lower() != "python":
            declarations.runtime.setdefault(normalize_package_name(dep), relpath(path, root))
    for group_name, group in poetry.get("group", {}).items():
        target = declarations.dev if group_name in {"dev", "test", "tests"} else declarations.optional
        for dep in group.get("dependencies", {}):
            target.setdefault(normalize_package_name(dep), relpath(path, root))
    for dep in poetry.get("dev-dependencies", {}):
        declarations.dev.setdefault(normalize_package_name(dep), relpath(path, root))
    for target in poetry.get("scripts", {}).values():
        match = SCRIPT_TARGET_RE.match(str(target))
        if match:
            _add_script_target(declarations, str(target), match.group(1))


def _parse_setup_cfg(path: Path, root: Path, declarations: DependencyDeclarations) -> None:
    declarations.files.append(relpath(path, root))
    parser = configparser.ConfigParser()
    parser.read(path)
    if parser.has_option("options", "install_requires"):
        for line in parser.get("options", "install_requires").splitlines():
            name = _requirement_name(line)
            if name:
                declarations.runtime.setdefault(name, relpath(path, root))
    if parser.has_section("options.entry_points"):
        for _, value in parser.items("options.entry_points"):
            for line in value.splitlines():
                match = SCRIPT_TARGET_RE.search(line)
                if match:
                    _add_script_target(declarations, line, match.group(1))


def _requirement_name(line: str) -> str | None:
    stripped = line.split("#", 1)[0].strip()
    if not stripped or stripped.startswith(("-", "git+", "http:", "https:")):
        return None
    if ";" in stripped:
        stripped = stripped.split(";", 1)[0].strip()
    if "[" in stripped:
        stripped = stripped.split("[", 1)[0]
    match = REQ_NAME_RE.match(stripped)
    return normalize_package_name(match.group(1)) if match else None


def _import_location(record: ImportRecord) -> dict[str, Any]:
    return {
        "path": record.path,
        "line": record.line,
        "module": record.raw_module,
        "type_checking": record.type_checking,
        "guarded": record.guarded,
        "test": _is_test_path(record.path),
    }


def _dependency_policy(records: list[ImportRecord]) -> str:
    if records and all(_is_test_path(record.path) for record in records):
        return "test-only"
    if records and all(record.type_checking for record in records):
        return "type-only"
    if any(record.guarded for record in records):
        return "optional-guarded"
    return "runtime"


def _add_script_target(declarations: DependencyDeclarations, raw_target: str, module: str) -> None:
    symbol = raw_target.split(":", 1)[1].split("[", 1)[0].strip() if ":" in raw_target else "main"
    declarations.scripts.append(module)
    declarations.script_targets.append((module, symbol))


def _is_test_path(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


FALLBACK_STDLIB = {
    "abc",
    "argparse",
    "ast",
    "asyncio",
    "collections",
    "configparser",
    "contextlib",
    "csv",
    "dataclasses",
    "datetime",
    "enum",
    "fnmatch",
    "functools",
    "hashlib",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "os",
    "pathlib",
    "queue",
    "re",
    "shutil",
    "sqlite3",
    "statistics",
    "subprocess",
    "sys",
    "tempfile",
    "threading",
    "time",
    "tokenize",
    "tomllib",
    "types",
    "typing",
    "unittest",
    "urllib",
    "uuid",
    "xml",
}
