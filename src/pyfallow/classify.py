from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from .models import CONFIDENCE_ORDER, RULES

FIX_PLAN_SCHEMA_VERSION = "1.0"
CLASSIFICATION_GROUPS = ("auto_safe", "review_needed", "blocking", "manual_only")

T = TypeVar("T")

BLOCKING_RULES = {
    "parse-error",
    "config-error",
    "unresolved-import",
    "missing-runtime-dependency",
    "dev-dependency-used-in-runtime",
}

REVIEW_NEEDED_RULES = {
    "dynamic-import",
    "production-imports-test-code",
    "missing-type-dependency",
    "missing-test-dependency",
    "optional-dependency-used-in-runtime",
    "runtime-dependency-used-only-in-tests",
    "runtime-dependency-used-only-for-types",
    "unused-runtime-dependency",
    "duplicate-code",
    "high-cyclomatic-complexity",
    "high-cognitive-complexity",
    "large-function",
    "large-file",
    "risky-hotspot",
}

MANUAL_ONLY_RULES = {"framework-entrypoint-detected"}


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    decision: str
    rationale: str
    minimal_patch: dict[str, Any] | None
    investigation_hints: list[str]
    fix_options: list[dict[str, str]]


def group_by_classification(
    issues: Iterable[dict[str, Any]],
    item_factory: Callable[[dict[str, Any], ClassificationResult], T],
) -> dict[str, list[T]]:
    groups: dict[str, list[T]] = {name: [] for name in CLASSIFICATION_GROUPS}
    for issue in issues:
        classification = classify_finding(issue)
        groups[classification.decision].append(item_factory(issue, classification))
    return groups


def flatten_classification_groups(groups: Mapping[str, Sequence[T]]) -> list[T]:
    return [item for name in CLASSIFICATION_GROUPS for item in groups.get(name, [])]


def classify_finding(issue: dict[str, Any]) -> ClassificationResult:
    rule = issue["rule"]
    decision, rationale = _decision_and_rationale(issue)
    return ClassificationResult(
        decision=decision,
        rationale=rationale,
        minimal_patch=_minimal_patch(issue, decision),
        investigation_hints=_render_templates(INVESTIGATION_HINTS.get(rule, DEFAULT_INVESTIGATION_HINTS), issue),
        fix_options=_render_fix_options(FIX_OPTIONS.get(rule, DEFAULT_FIX_OPTIONS), issue),
    )


def agent_fix_plan(result: dict[str, Any]) -> dict[str, Any]:
    groups = group_by_classification(result["issues"], _plan_item)
    plan_items = flatten_classification_groups(groups)

    plan: dict[str, Any] = {
        "schema_version": FIX_PLAN_SCHEMA_VERSION,
        "tool": "pyfallow",
        "version": result["version"],
        "source_report_schema_version": result["schema_version"],
        "summary": {
            "auto_safe_count": len(groups["auto_safe"]),
            "review_needed_count": len(groups["review_needed"]),
            "blocking_count": len(groups["blocking"]),
            "manual_only_count": len(groups["manual_only"]),
            "total": len(plan_items),
        },
        "auto_safe": groups["auto_safe"],
        "review_needed": groups["review_needed"],
        "blocking": groups["blocking"],
        "manual_only": groups["manual_only"],
        "limitations": list(result.get("limitations", [])),
    }
    diff_scope = result.get("analysis", {}).get("diff_scope")
    if diff_scope and diff_scope.get("since") is not None:
        plan["diff_scope"] = diff_scope
    return plan


def _decision_and_rationale(issue: dict[str, Any]) -> tuple[str, str]:
    rule = issue["rule"]
    confidence = issue["confidence"]
    if rule in BLOCKING_RULES:
        return "blocking", "deterministic structural signal; resolve before commit alongside tests, lint, and type checks."
    if rule == "circular-dependency":
        if issue.get("evidence", {}).get("type_checking_imports_contributed"):
            return "review_needed", "cycle appears to involve type-checking imports; review before changing runtime structure."
        return "blocking", "runtime import cycle risk; resolve before commit or explicitly waive."
    if rule == "boundary-violation":
        if issue["severity"] == "error":
            return "blocking", "configured architecture boundary is enforced as an error."
        return "review_needed", "configured architecture boundary is advisory at this severity."
    if rule == "stale-suppression":
        return "auto_safe", "stale suppression has high-confidence evidence and a local comment-only patch."
    if rule == "unused-symbol":
        return _unused_symbol_decision(issue)
    if rule == "unused-module":
        if CONFIDENCE_ORDER[confidence] < CONFIDENCE_ORDER["medium"]:
            return "manual_only", "low-confidence dead-module signal; keep as context, not an action."
        return "review_needed", "module reachability is static and should be reviewed before removal."
    if rule in REVIEW_NEEDED_RULES:
        return "review_needed", "use this deterministic signal as review input alongside the rest of the toolchain."
    if rule in MANUAL_ONLY_RULES:
        return "manual_only", "informational framework signal; no direct cleanup action."
    return "review_needed", "unmapped rule defaults to review-needed to avoid unsafe automation."


def _unused_symbol_decision(issue: dict[str, Any]) -> tuple[str, str]:
    confidence = issue["confidence"]
    if CONFIDENCE_ORDER[confidence] < CONFIDENCE_ORDER["medium"]:
        return "manual_only", "low-confidence unused-symbol signal; keep as context, not an action."
    state = issue.get("evidence", {}).get("state", {})
    if state.get("framework_managed") or issue.get("evidence", {}).get("framework_managed"):
        return "review_needed", "symbol appears framework-managed; review before editing."
    if state.get("entrypoint_managed") or issue.get("evidence", {}).get("entrypoint_managed"):
        return "review_needed", "symbol is tied to an entrypoint; review before editing."
    if state.get("public_api") or issue.get("evidence", {}).get("public_api"):
        return "review_needed", "symbol may be public API; review external callers before editing."
    if state.get("dynamic_uncertain") or issue.get("evidence", {}).get("dynamic_uncertain"):
        return "review_needed", "dynamic usage uncertainty prevents automatic cleanup."
    if confidence == "high":
        return "auto_safe", "high-confidence unused symbol without framework, entrypoint, public API, or dynamic uncertainty flags."
    return "review_needed", "medium-confidence unused-symbol signal; review before cleanup."


def _plan_item(issue: dict[str, Any], classification: ClassificationResult) -> dict[str, Any]:
    item = {
        "fingerprint": issue["fingerprint"],
        "rule": issue["rule"],
        "id": issue["id"],
        "file": issue.get("path"),
        "line": _line(issue),
        "symbol": issue.get("symbol"),
        "module": issue.get("module"),
        "severity": issue["severity"],
        "confidence": issue["confidence"],
        "one_liner": _one_liner(issue),
        "rationale": classification.rationale,
        "minimal_patch": classification.minimal_patch,
        "investigation_hints": classification.investigation_hints,
        "fix_options": classification.fix_options,
    }
    if classification.decision == "blocking":
        item["evidence"] = issue.get("evidence", {})
    distribution = issue.get("evidence", {}).get("distribution")
    if distribution:
        item["distribution"] = distribution
    return item


def _minimal_patch(issue: dict[str, Any], decision: str) -> dict[str, Any] | None:
    if decision != "auto_safe" or issue["rule"] != "stale-suppression" or not issue.get("path"):
        return None
    evidence = issue.get("evidence", {})
    before = evidence.get("line_text") or evidence.get("suppression") or ""
    suppression = evidence.get("suppression", "")
    after = before.replace(suppression, "", 1).rstrip()
    if not after:
        return {
            "type": "delete_line",
            "file": issue["path"],
            "line": _line(issue),
            "before": before,
            "after": None,
        }
    return {
        "type": "replace_line",
        "file": issue["path"],
        "line": _line(issue),
        "before": before,
        "after": after,
    }


def _one_liner(issue: dict[str, Any]) -> str:
    if issue["rule"] == "stale-suppression":
        return f"Suppression at line {_line(issue)} does not match any current finding."
    if issue["rule"] == "missing-runtime-dependency":
        distribution = issue.get("evidence", {}).get("distribution")
        if distribution:
            return f"Runtime import uses '{distribution}', but it is not declared as a runtime dependency."
    return issue["message"]


def _line(issue: dict[str, Any]) -> int:
    return int(issue.get("range", {}).get("start", {}).get("line") or 1)


def _format_fields(issue: dict[str, Any]) -> dict[str, Any]:
    evidence = issue.get("evidence", {})
    return {
        "file": issue.get("path") or ".",
        "line": _line(issue),
        "symbol": issue.get("symbol") or "the symbol",
        "module": issue.get("module") or evidence.get("module") or "the module",
        "distribution": evidence.get("distribution") or evidence.get("imported_module") or "the package",
        "rule": issue["rule"],
    }


def _render_templates(templates: list[str], issue: dict[str, Any]) -> list[str]:
    fields = _format_fields(issue)
    return [template.format(**fields) for template in templates]


def _render_fix_options(options: list[tuple[str, str]], issue: dict[str, Any]) -> list[dict[str, str]]:
    fields = _format_fields(issue)
    return [{"type": option_type, "description": description.format(**fields)} for option_type, description in options]


DEFAULT_INVESTIGATION_HINTS = [
    "Review this finding in context with tests, lint, type checking, and recent diff intent.",
]

INVESTIGATION_HINTS = {
    "unused-symbol": [
        "Search for '{symbol}' across templates, configs, docs, and generated entrypoint names.",
        "Check whether '{symbol}' is exported through package __init__.py or __all__.",
        "Check whether decorators or framework registration consume '{symbol}'.",
    ],
    "unused-module": [
        "Search for dynamic imports or plugin configuration that mentions '{module}' or '{file}'.",
        "Check whether the module is intentionally public API or framework-discovered.",
    ],
    "duplicate-code": [
        "Compare duplicate locations for shared concept vs intentionally similar but separate logic.",
        "Check git history to see whether the duplication is new slop or long-standing design.",
    ],
    "circular-dependency": [
        "Inspect the import path and identify the lowest-level shared concept.",
        "Prefer extracting a small third module or inverting dependency direction over moving imports randomly.",
    ],
    "missing-runtime-dependency": [
        "Check whether '{distribution}' is a real third-party dependency or a mistaken local import.",
        "If this came from an agent edit, verify the imported symbol exists before declaring a new dependency.",
    ],
    "boundary-violation": [
        "Check the configured boundary rule before moving code.",
        "Prefer moving shared policy behind an interface over widening the dependency direction.",
    ],
    "stale-suppression": [
        "Confirm the suppression is no longer needed, then remove the comment.",
    ],
}

DEFAULT_FIX_OPTIONS = [
    ("review", "Review the finding and decide whether to change code, configuration, or suppression."),
]

FIX_OPTIONS = {
    "missing-runtime-dependency": [
        ("declare", "Add '{distribution}' to project.dependencies in pyproject.toml if it is truly runtime code."),
        ("remove_import", "Remove the import if it is unused or was hallucinated by an agent."),
        ("guard", "Wrap the import in try/except ImportError if the dependency is intentionally optional."),
        ("rename", "If this was meant to be local code, fix the import path instead of declaring a dependency."),
    ],
    "circular-dependency": [
        ("extract_interface", "Extract shared types or policy to a third module."),
        ("invert_dependency", "Reverse the dependency direction so the higher-level module owns the abstraction."),
        ("type_checking_only", "If usage is type-hint only, move it under TYPE_CHECKING."),
    ],
    "unused-symbol": [
        ("remove", "Remove '{symbol}' if confirmed unused outside Python static analysis."),
        ("export", "Add '{symbol}' to an explicit public API only if it is intentionally external."),
        ("suppress", "Add a targeted suppression only for framework or plugin-managed symbols."),
    ],
    "unused-module": [
        ("remove", "Remove '{file}' only after checking dynamic imports and framework discovery."),
        ("entrypoint", "Add an explicit entrypoint if the module is reached outside static imports."),
        ("suppress", "Add a targeted suppression if the module is intentionally loaded dynamically."),
    ],
    "duplicate-code": [
        ("extract", "Extract a shared helper only if both blocks express the same concept."),
        ("accept", "Keep the duplication if similar shape hides different product meaning."),
    ],
    "stale-suppression": [
        ("remove_suppression", "Remove the stale suppression comment."),
    ],
    "boundary-violation": [
        ("move_dependency", "Move the dependency behind an allowed module boundary."),
        ("extract_interface", "Extract a shared interface or policy module allowed by the rule."),
        ("adjust_rule", "Adjust the boundary rule only if the architecture policy changed."),
    ],
}
