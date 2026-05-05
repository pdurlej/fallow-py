from __future__ import annotations

from pathlib import Path
from typing import Any

from pyfallow.analysis import filter_result
from pyfallow.classify import ClassificationResult, flatten_classification_groups, group_by_classification
from pyfallow.config import load_config
from pyfallow.predict import verify_imports

from .context import agent_context_impl
from .remediation import explain_finding_impl
from .runtime import analyze_report, cached_report, issue_sort_key
from .safety import safe_to_remove_impl
from .schemas import AnalysisResult, DiffScope, Finding, SummaryCounts, VerifyResult


def analyze_diff_impl(
    root: str | Path,
    since: str = "HEAD~1",
    min_confidence: str = "medium",
    max_findings: int = 50,
) -> AnalysisResult:
    result = analyze_report(root, since=since)
    filtered = filter_result(result, min_confidence, "info")
    ordered_issues = sorted(filtered["issues"], key=issue_sort_key)
    truncated = len(ordered_issues) > max_findings
    grouped = group_by_classification(ordered_issues[:max_findings], _finding_model)
    finding_models = flatten_classification_groups(grouped)
    return AnalysisResult(
        summary=SummaryCounts(**filtered["summary"]),
        diff_scope=DiffScope(**filtered["analysis"].get("diff_scope", {})),
        auto_safe=grouped["auto_safe"],
        review_needed=grouped["review_needed"],
        blocking=grouped["blocking"],
        manual_only=grouped["manual_only"],
        findings=finding_models,
        truncated=truncated,
        next_cursor=None,
    )


def verify_imports_impl(root: str | Path, file: str, planned_imports: list[str]) -> VerifyResult:
    config = load_config(root)
    result = verify_imports(config, Path(file), list(planned_imports), report=cached_report(root))
    return VerifyResult(**result.to_dict())


def _finding_model(issue: dict[str, Any], classification: ClassificationResult) -> Finding:
    payload = dict(issue)
    payload["classification"] = classification.decision
    return Finding(**payload)
