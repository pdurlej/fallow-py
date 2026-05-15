from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from . import VERSION
from .schemas import AgentContext, AnalysisResult, Classification, Remediation, VerifyResult
from .runtime import cached_report, module_graph
from .tools import (
    agent_context_impl,
    analyze_diff_impl,
    explain_finding_impl,
    safe_to_remove_impl,
    verify_imports_impl,
)

SERVER_INSTRUCTIONS = (
    "Use pyfallow tools before committing or showing Python code changes. "
    "Treat high-confidence findings as actionable and low-confidence findings as review context."
)


def build_server(default_root: str | Path | None = None) -> FastMCP:
    server = FastMCP("pyfallow", version=VERSION, instructions=SERVER_INSTRUCTIONS)

    def root_or_default(root: str | Path | None = None) -> str:
        return str(Path(root or default_root or ".").resolve())

    @server.tool
    def analyze_diff(
        root: str | None = None,
        since: str = "HEAD~1",
        min_confidence: str = "medium",
        max_findings: int = 50,
    ) -> AnalysisResult:
        return analyze_diff_impl(root_or_default(root), since, min_confidence, max_findings)

    @server.tool
    def agent_context(root: str | None = None, scope: str = "diff", max_findings: int = 20) -> AgentContext:
        return agent_context_impl(root_or_default(root), scope, max_findings)

    @server.tool
    def explain_finding(root: str | None = None, fingerprint: str = "") -> Remediation:
        return explain_finding_impl(root_or_default(root), fingerprint)

    @server.tool
    def verify_imports(root: str | None = None, file: str = "", planned_imports: list[str] | None = None) -> VerifyResult:
        return verify_imports_impl(root_or_default(root), file, planned_imports or [])

    @server.tool
    def safe_to_remove(root: str | None = None, fingerprints: list[str] | None = None) -> dict[str, Classification]:
        return safe_to_remove_impl(root_or_default(root), fingerprints or [])

    @server.resource("pyfallow://report/current/{root}")
    def current_report(root: str) -> dict[str, Any]:
        return cached_report(root_or_default(root))

    @server.resource("pyfallow://module-graph/{root}")
    def current_module_graph(root: str) -> dict[str, Any]:
        return module_graph(root_or_default(root))

    @server.prompt("pre-commit-check")
    def pre_commit_check() -> str:
        return (
            "Before committing Python changes, call pyfallow.analyze_diff(since='HEAD~1'). "
            "Auto-fix only findings classified as auto_safe, show review_needed findings to the user, "
            "and block the commit when blocking findings remain."
        )

    @server.prompt("pr-cleanup")
    def pr_cleanup() -> str:
        return (
            "Before pushing a PR branch, call pyfallow.analyze_diff(since='main') and "
            "pyfallow.agent_context(scope='diff'). Auto-fix safe findings, inspect review_needed "
            "findings for false positives, and summarize remaining risks for the user."
        )

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pyfallow-mcp", description="MCP server for pyfallow.")
    parser.add_argument("--root", default=".", help="Default analysis root for tools/resources.")
    parser.add_argument("--version", action="version", version=f"pyfallow-mcp {VERSION}")
    args = parser.parse_args(argv)
    build_server(args.root).run()
    return 0
