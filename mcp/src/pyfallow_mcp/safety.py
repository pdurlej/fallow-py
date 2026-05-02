from __future__ import annotations

from pathlib import Path
from typing import Any

from pyfallow.models import CONFIDENCE_ORDER

from .runtime import analyze_report
from .schemas import Classification


def safe_to_remove_impl(root: str | Path, fingerprints: list[str]) -> dict[str, Classification]:
    result = analyze_report(root)
    by_fingerprint = {issue["fingerprint"]: issue for issue in result["issues"]}
    return {
        fingerprint: safe_classification(fingerprint, by_fingerprint.get(fingerprint))
        for fingerprint in fingerprints
    }


def safe_classification(fingerprint: str, issue: dict[str, Any] | None) -> Classification:
    if not issue:
        return Classification(fingerprint=fingerprint, decision="manual-only", rationale="Fingerprint was not found.")
    if safe_auto_issue(issue):
        return Classification(fingerprint=fingerprint, decision="safe-auto", rationale="High-confidence dead-code finding without unsafe state evidence.")
    if issue.get("confidence") == "medium":
        return Classification(fingerprint=fingerprint, decision="review-needed", rationale="Medium-confidence finding requires review.")
    return Classification(fingerprint=fingerprint, decision="manual-only", rationale="Low confidence, dynamic uncertainty, public API, or non-dead-code rule.")


def safe_auto_issue(issue: dict[str, Any]) -> bool:
    if issue["rule"] not in {"unused-module", "unused-symbol"}:
        return False
    if CONFIDENCE_ORDER[issue["confidence"]] < CONFIDENCE_ORDER["high"]:
        return False
    evidence = issue.get("evidence", {})
    state = evidence.get("state", {})
    unsafe_flags = {"public_api", "framework_managed", "entrypoint_managed", "dynamic_uncertain"}
    return not any(evidence.get(flag) or state.get(flag) for flag in unsafe_flags)
