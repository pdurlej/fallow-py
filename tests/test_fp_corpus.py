from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pyfallow.analysis import analyze
from pyfallow.config import load_config
from pyfallow.models import CONFIDENCE_ORDER

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "benchmarks" / "fp-cases"
EXPECTED_CASES = {
    "celery-shared-task",
    "dataclass-only-fields",
    "django-management-command",
    "fastapi-route",
    "namespace-package-ambiguity",
    "optional-dependency-guard",
    "package-public-api",
    "protocol-class",
    "type-checking-only-import",
}


def case_ids() -> list[str]:
    return sorted(path.name for path in CORPUS_ROOT.iterdir() if path.is_dir())


def test_fp_corpus_case_set_is_explicit() -> None:
    assert set(case_ids()) == EXPECTED_CASES


@pytest.mark.parametrize("case", case_ids())
def test_fp_corpus_expected_behavior(case: str) -> None:
    root = CORPUS_ROOT / case
    expected = json.loads((root / "expected.json").read_text(encoding="utf-8"))
    result = analyze(load_config(root))

    assert result["summary"]["errors"] <= expected.get("max_errors", 0), _issue_lines(result["issues"])

    for framework in expected.get("required_frameworks", []):
        assert framework in result["analysis"]["frameworks_detected"]

    ambiguity_modules = {item["module"] for item in result["analysis"].get("module_ambiguities", [])}
    for module in expected.get("required_module_ambiguities", []):
        assert module in ambiguity_modules

    for selector in expected.get("required_findings", []):
        assert any(_matches(issue, selector) for issue in result["issues"]), (
            f"{case}: required finding not found: {selector}\n{_issue_lines(result['issues'])}"
        )

    for selector in expected.get("forbidden_findings", []):
        assert not any(_matches(issue, selector) for issue in result["issues"]), (
            f"{case}: forbidden finding was emitted: {selector}\n{_issue_lines(result['issues'])}"
        )

    for expectation in expected.get("max_confidence_findings", []):
        max_confidence = expectation["max_confidence"]
        selector = {key: value for key, value in expectation.items() if key != "max_confidence"}
        for issue in [item for item in result["issues"] if _matches(item, selector)]:
            assert CONFIDENCE_ORDER[issue["confidence"]] <= CONFIDENCE_ORDER[max_confidence], (
                f"{case}: expected {selector} at max confidence {max_confidence}, "
                f"got {issue['confidence']}\n{_issue_lines(result['issues'])}"
            )


def _matches(issue: dict[str, Any], selector: dict[str, Any]) -> bool:
    for key, expected in selector.items():
        if key == "distribution":
            actual = issue.get("evidence", {}).get("distribution")
        elif key == "message_contains":
            actual = issue.get("message", "")
            if expected not in actual:
                return False
            continue
        else:
            actual = issue.get(key)
        if actual != expected:
            return False
    return True


def _issue_lines(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "No issues emitted."
    return "\n".join(
        f"{issue['rule']} {issue['confidence']} {issue.get('path')} "
        f"{issue.get('module')} {issue.get('symbol')}"
        for issue in issues
    )
