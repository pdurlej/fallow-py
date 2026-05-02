from __future__ import annotations

from pathlib import Path

from .config import PythonConfig
from .paths import is_test_path, matches_any, relpath


COMMON_SOURCE_DIRS = ["src", "app", "backend", "server", "service"]


def discover_source_roots(config: PythonConfig) -> list[Path]:
    root = config.root
    if config.roots:
        roots = [(root / item).resolve() for item in config.roots]
        return sorted([path for path in roots if path.exists()], key=lambda p: p.as_posix())

    candidates: list[Path] = []
    for name in COMMON_SOURCE_DIRS:
        path = root / name
        if path.is_dir() and any(path.rglob("*.py")):
            candidates.append(path.resolve())

    root_py_files = list(root.glob("*.py"))
    package_dirs = [
        item
        for item in root.iterdir()
        if item.is_dir()
        and not item.name.startswith(".")
        and (item / "__init__.py").exists()
        and not matches_any(item.name + "/", config.ignore)
    ] if root.exists() else []
    if root_py_files or package_dirs or not candidates:
        candidates.append(root.resolve())

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in sorted(candidates, key=lambda p: len(p.as_posix()), reverse=True):
        key = path.as_posix()
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def discover_python_files(config: PythonConfig, source_roots: list[Path]) -> list[Path]:
    root = config.root
    files: dict[str, Path] = {}
    for source_root in source_roots:
        if not source_root.exists():
            continue
        for path in source_root.rglob("*.py"):
            relative = relpath(path, root)
            if matches_any(relative, config.ignore):
                continue
            if _ignored_by_parent(relative, config.ignore):
                continue
            if not config.include_tests and is_test_path(relative):
                # Tests are excluded from dead-code reporting by default, but dependency
                # classification still benefits from seeing explicitly configured test roots.
                pass
            files[relative] = path.resolve()
    return [files[key] for key in sorted(files)]


def _ignored_by_parent(relative: str, patterns: list[str]) -> bool:
    parts = relative.split("/")
    prefixes = ["/".join(parts[:index]) + "/" for index in range(1, len(parts))]
    return any(matches_any(prefix, patterns) for prefix in prefixes)
