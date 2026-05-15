from __future__ import annotations

from pathlib import Path

from .models import ImportRecord, ModuleInfo
from .paths import relpath


class ModuleResolver:
    def __init__(self, root: Path, source_roots: list[Path]) -> None:
        self.root = root.resolve()
        self.source_roots = sorted([path.resolve() for path in source_roots], key=lambda p: len(p.parts), reverse=True)
        self.module_to_path: dict[str, str] = {}
        self.path_to_module: dict[str, str] = {}

    def module_name_for_path(self, path: Path) -> tuple[str, str, bool]:
        resolved = path.resolve()
        source_root = self.root
        for candidate in self.source_roots:
            try:
                resolved.relative_to(candidate)
            except ValueError:
                continue
            source_root = candidate
            break
        relative = resolved.relative_to(source_root)
        parts = list(relative.with_suffix("").parts)
        is_init = parts[-1] == "__init__"
        if is_init:
            parts = parts[:-1]
        module = ".".join(parts) if parts else resolved.parent.name
        return module or resolved.stem, relpath(source_root, self.root), is_init

    def register(self, module: ModuleInfo) -> None:
        self.module_to_path[module.module] = module.path
        self.path_to_module[module.path] = module.module

    def resolve_import(self, record: ImportRecord, importer_is_init: bool = False) -> ImportRecord:
        if record.dynamic and not record.dynamic_literal:
            record.classification = "dynamic"
            return record
        if record.level:
            return self._resolve_relative(record, importer_is_init)
        return self._resolve_absolute(record)

    def _resolve_absolute(self, record: ImportRecord) -> ImportRecord:
        raw = record.raw_module or ""
        symbol = record.imported_symbol
        if record.kind == "from" and symbol:
            submodule = f"{raw}.{symbol}" if raw else symbol
            if submodule in self.module_to_path:
                return self._mark_local(record, submodule, None)
            if raw in self.module_to_path:
                return self._mark_local(record, raw, symbol)
        for candidate in _prefixes(raw):
            if candidate in self.module_to_path:
                return self._mark_local(record, candidate, symbol if candidate == raw else None)
        return record

    def _resolve_relative(self, record: ImportRecord, importer_is_init: bool) -> ImportRecord:
        package = record.importer if importer_is_init else record.importer.rpartition(".")[0]
        package_parts = package.split(".") if package else []
        if record.level > 1:
            package_parts = package_parts[: max(0, len(package_parts) - record.level + 1)]
        base = ".".join(part for part in package_parts if part)
        raw = record.raw_module or ""
        target_base = ".".join(part for part in [base, raw] if part)
        symbol = record.imported_symbol
        if record.kind == "from" and symbol:
            submodule = ".".join(part for part in [target_base, symbol] if part)
            if submodule in self.module_to_path:
                return self._mark_local(record, submodule, None)
            if target_base in self.module_to_path:
                return self._mark_local(record, target_base, symbol)
        if target_base in self.module_to_path:
            return self._mark_local(record, target_base, symbol)
        for candidate in _prefixes(target_base):
            if candidate in self.module_to_path:
                return self._mark_local(record, candidate, None)
        return record

    def _mark_local(self, record: ImportRecord, module: str, symbol: str | None) -> ImportRecord:
        record.target_module = module
        record.target_path = self.module_to_path[module]
        record.imported_symbol = symbol
        record.classification = "local"
        return record


def _prefixes(module: str) -> list[str]:
    parts = module.split(".") if module else []
    return [".".join(parts[:index]) for index in range(len(parts), 0, -1)]
