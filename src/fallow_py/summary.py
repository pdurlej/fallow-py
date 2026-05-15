from __future__ import annotations

from typing import Any


def summary_from_issue_dicts(issues: list[dict[str, Any]], duplicate_groups: int) -> dict[str, int]:
    counts = {
        "total_issues": len(issues),
        "errors": 0,
        "warnings": 0,
        "info": 0,
        "parse_errors": 0,
        "config_errors": 0,
        "unused_modules": 0,
        "unused_symbols": 0,
        "missing_dependencies": 0,
        "unused_dependencies": 0,
        "circular_dependencies": 0,
        "duplicate_groups": duplicate_groups,
        "complexity_hotspots": 0,
        "boundary_violations": 0,
        "stale_suppressions": 0,
    }
    for issue in issues:
        _count_issue(counts, issue)
    return counts


def _count_issue(counts: dict[str, int], issue: dict[str, Any]) -> None:
    severity = issue["severity"]
    counts["errors" if severity == "error" else "warnings" if severity == "warning" else "info"] += 1
    rule = issue["rule"]
    if rule == "parse-error":
        counts["parse_errors"] += 1
    elif rule == "config-error":
        counts["config_errors"] += 1
    elif rule == "unused-module":
        counts["unused_modules"] += 1
    elif rule == "unused-symbol":
        counts["unused_symbols"] += 1
    elif rule in MISSING_DEPENDENCY_RULES:
        counts["missing_dependencies"] += 1
    elif rule in UNUSED_DEPENDENCY_RULES:
        counts["unused_dependencies"] += 1
    elif rule == "circular-dependency":
        counts["circular_dependencies"] += 1
    elif rule in COMPLEXITY_RULES:
        counts["complexity_hotspots"] += 1
    elif rule == "boundary-violation":
        counts["boundary_violations"] += 1
    elif rule == "stale-suppression":
        counts["stale_suppressions"] += 1


MISSING_DEPENDENCY_RULES = {
    "missing-runtime-dependency",
    "missing-type-dependency",
    "missing-test-dependency",
    "dev-dependency-used-in-runtime",
    "optional-dependency-used-in-runtime",
}

UNUSED_DEPENDENCY_RULES = {
    "runtime-dependency-used-only-in-tests",
    "runtime-dependency-used-only-for-types",
    "unused-runtime-dependency",
}

COMPLEXITY_RULES = {
    "high-cyclomatic-complexity",
    "high-cognitive-complexity",
    "large-function",
    "large-file",
    "risky-hotspot",
}
