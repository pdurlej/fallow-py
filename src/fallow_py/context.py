from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .config import PythonConfig
from .dependencies import DependencyDeclarations
from .graph import ImportGraph
from .models import ModuleInfo


@dataclass(slots=True)
class AnalysisContext:
    config: PythonConfig
    source_roots: tuple[Path, ...]
    modules: Mapping[str, ModuleInfo]
    graph: ImportGraph
    declarations: DependencyDeclarations
    entrypoints: tuple[dict, ...]
    entry_modules: tuple[str, ...]
    explicit_entrypoints: bool
    entrypoint_symbols: Mapping[str, frozenset[str]]
