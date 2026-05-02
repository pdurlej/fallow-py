from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pyfallow.analysis import analyze
from pyfallow.config import load_config
from pyfallow.models import SEVERITY_ORDER

from .schemas import Finding

CACHE_TTL_SECONDS = 60
REPORT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def analyze_report(root: str | Path, since: str | None = None) -> dict[str, Any]:
    config = load_config(root)
    if since:
        config.since_ref = since
        config.changed_only_requested = True
    return analyze(config)


def cached_report(root: str | Path) -> dict[str, Any]:
    key = str(Path(root).resolve())
    now = time.monotonic()
    cached = REPORT_CACHE.get(key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    result = analyze_report(key)
    REPORT_CACHE[key] = (now, result)
    return result


def module_graph(root: str | Path) -> dict[str, Any]:
    graph = cached_report(root)["graphs"]
    return {
        "modules": graph.get("modules", []),
        "edges": graph.get("edges", []),
        "cycles": graph.get("cycles", []),
    }


def findings(issues: list[dict[str, Any]]) -> list[Finding]:
    return [Finding(**issue) for issue in sorted(issues, key=issue_sort_key)]


def issue_sort_key(issue: dict[str, Any]) -> tuple[int, str, str, int, str]:
    return (
        -SEVERITY_ORDER[issue["severity"]],
        issue["id"],
        issue.get("path") or "",
        issue.get("range", {}).get("start", {}).get("line", 1),
        issue.get("fingerprint", ""),
    )
