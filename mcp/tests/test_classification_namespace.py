"""MCP classification namespace drift detection.

MCP classification fields must mirror core CLASSIFICATION_GROUPS. If this test
fails, a transport-specific schema or helper has drifted from the core
classification policy; see .codex/WORKFLOW.md rule #11.
"""

from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from pyfallow.classify import CLASSIFICATION_GROUPS
from pyfallow_mcp.schemas import Classification, Finding, Remediation

CORE_GROUPS = set(CLASSIFICATION_GROUPS)


def _literal_args(annotation: Any) -> set[str]:
    if get_origin(annotation) is Literal:
        return set(get_args(annotation))
    for arg in get_args(annotation):
        if get_origin(arg) is Literal:
            return set(get_args(arg))
    raise AssertionError(f"Could not extract Literal from annotation: {annotation!r}")


def test_classification_decision_mirrors_core_groups() -> None:
    args = _literal_args(Classification.model_fields["decision"].annotation)
    assert args == CORE_GROUPS, (
        f"Classification.decision diverges from core: extra={args - CORE_GROUPS}, "
        f"missing={CORE_GROUPS - args}"
    )


def test_finding_classification_mirrors_core_groups() -> None:
    args = _literal_args(Finding.model_fields["classification"].annotation)
    assert args == CORE_GROUPS


def test_remediation_classification_mirrors_core_groups() -> None:
    args = _literal_args(Remediation.model_fields["classification"].annotation)
    assert args == CORE_GROUPS


def test_safe_classification_canary_returns_auto_safe_for_clean_high_confidence() -> None:
    """Canary: safe_classification must return the core underscore namespace."""
    from pyfallow_mcp.safety import safe_classification

    issue = {
        "rule": "unused-symbol",
        "severity": "warning",
        "confidence": "high",
        "fingerprint": "canary_fp",
        "evidence": {
            "state": {
                "framework_managed": False,
                "entrypoint_managed": False,
                "public_api": False,
                "dynamic_uncertain": False,
            }
        },
    }

    result = safe_classification("canary_fp", issue)

    assert result.decision == "auto_safe", (
        f"safe_classification must return underscore namespace, got {result.decision!r}."
    )
