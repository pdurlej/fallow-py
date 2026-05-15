from __future__ import annotations

from typing import Any

from fallow_py.models import RULES

from .schemas import FixOption
from .safety import safe_auto_issue


def investigation_hints(issue: dict[str, Any]) -> list[str]:
    path = issue.get("path") or "."
    hints = [f"Inspect {path} and this finding's evidence before editing."]
    symbol = issue.get("symbol")
    if symbol:
        hints.append(f"Search for static and dynamic references to {symbol!r}.")
    return hints + rule_hints(issue)


def rule_hints(issue: dict[str, Any]) -> list[str]:
    rule = issue["rule"]
    if rule == "circular-dependency":
        return ["Inspect every import edge in evidence.cycle_path before choosing a remediation."]
    if rule == "boundary-violation":
        return ["Prefer dependency inversion over adding boundary exceptions."]
    if RULES[rule]["category"] == "dependencies":
        return ["Compare imports against pyproject/requirements declarations before changing dependencies."]
    return []


def fix_options(issue: dict[str, Any]) -> list[FixOption]:
    rule = issue["rule"]
    if rule in {"unused-module", "unused-symbol"}:
        return [
            FixOption(description="Remove the unused code after checking framework and dynamic usage.", safe=safe_auto_issue(issue)),
            FixOption(description="Keep it and add a targeted suppression if it is intentionally dynamic.", safe=False),
        ]
    return [FixOption(description=fix_description(rule), safe=False)]


def fix_description(rule: str) -> str:
    if rule == "circular-dependency":
        return "Extract a shared interface or invert one dependency edge."
    if rule == "boundary-violation":
        return "Move the dependency behind an allowed interface or adapter."
    if RULES[rule]["category"] == "dependencies":
        return "Update dependency declarations or remove the import."
    if RULES[rule]["category"] == "health":
        return "Split the function or isolate branch-heavy policy."
    if rule == "duplicate-code":
        return "Deduplicate only when the blocks represent the same concept."
    return "Review the evidence and choose the smallest local fix."


def safety_notes(issue: dict[str, Any]) -> list[str]:
    notes = ["Static analysis may miss dynamic imports, reflection, and framework magic."]
    if issue["confidence"] == "low":
        notes.append("Low-confidence findings should not be auto-fixed.")
    if issue["rule"] in {"unused-module", "unused-symbol"}:
        notes.append("Deletion needs public API, entrypoint, and dynamic-access checks.")
    return notes
