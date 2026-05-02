from __future__ import annotations

from pathlib import Path

from pyfallow.analysis import filter_result
from pyfallow.config import load_config
from pyfallow.predict import verify_imports

from .context import agent_context_impl
from .remediation import explain_finding_impl
from .runtime import analyze_report, cached_report, findings
from .safety import safe_to_remove_impl
from .schemas import AnalysisResult, DiffScope, SummaryCounts, VerifyResult


def analyze_diff_impl(
    root: str | Path,
    since: str = "HEAD~1",
    min_confidence: str = "medium",
    max_findings: int = 50,
) -> AnalysisResult:
    result = analyze_report(root, since=since)
    filtered = filter_result(result, min_confidence, "info")
    finding_models = findings(filtered["issues"])
    truncated = len(finding_models) > max_findings
    return AnalysisResult(
        summary=SummaryCounts(**filtered["summary"]),
        findings=finding_models[:max_findings],
        diff_scope=DiffScope(**filtered["analysis"].get("diff_scope", {})),
        truncated=truncated,
        next_cursor=None,
    )


def verify_imports_impl(root: str | Path, file: str, planned_imports: list[str]) -> VerifyResult:
    config = load_config(root)
    result = verify_imports(config, Path(file), list(planned_imports), report=cached_report(root))
    return VerifyResult(**result.to_dict())
