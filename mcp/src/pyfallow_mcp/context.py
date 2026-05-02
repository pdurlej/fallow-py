from __future__ import annotations

from pathlib import Path
from typing import Any

from pyfallow.analysis import LIMITATIONS
from pyfallow.config import load_config
from pyfallow.models import RULES

from .runtime import analyze_report, findings
from .schemas import (
    AgentContext,
    ArchitectureMap,
    BoundaryRuleSummary,
    ExportRef,
    Finding,
    ProjectOverview,
    RiskItem,
)


def agent_context_impl(root: str | Path, scope: str = "diff", max_findings: int = 20) -> AgentContext:
    if scope not in {"diff", "full"}:
        raise ValueError("scope must be 'diff' or 'full'")
    result = analyze_report(root, since="HEAD~1" if scope == "diff" else None)
    issue_models = findings(result["issues"])
    return AgentContext(
        project_overview=_project_overview(result),
        architecture_map=_architecture_map(result, issue_models, max_findings),
        public_api=_public_api(result),
        boundary_rules=_boundary_rules(root),
        risk_map=[_risk_item(finding) for finding in _risk_findings(issue_models)[:max_findings]],
        dead_code_candidates=_dead_findings(issue_models)[:max_findings],
        dependency_findings=_dependency_findings(issue_models)[:max_findings],
        limitations=list(result.get("limitations", LIMITATIONS)),
    )


def _project_overview(result: dict[str, Any]) -> ProjectOverview:
    analysis = result["analysis"]
    return ProjectOverview(
        roots=analysis.get("source_roots", []),
        entrypoints=analysis.get("entrypoints", []),
        frameworks=analysis.get("frameworks_detected", []),
        dependency_files=analysis.get("dependency_files", []),
        modules_count=analysis.get("modules_analyzed", 0),
    )


def _architecture_map(
    result: dict[str, Any],
    issue_models: list[Finding],
    max_findings: int,
) -> ArchitectureMap:
    graph = result["graphs"]
    fan_in, fan_out = _fan_lists(graph.get("edges", []))
    return ArchitectureMap(
        cycles=graph.get("cycles", [])[:max_findings],
        high_fan_in=fan_in[:max_findings],
        high_fan_out=fan_out[:max_findings],
        hotspots=_risk_findings(issue_models)[:max_findings],
    )


def _public_api(result: dict[str, Any]) -> list[ExportRef]:
    return [ExportRef(**item) for item in result["graphs"].get("exports", [])[:50]]


def _risk_findings(issue_models: list[Finding]) -> list[Finding]:
    risk_rules = {
        "circular-dependency",
        "boundary-violation",
        "duplicate-code",
        "high-cyclomatic-complexity",
        "high-cognitive-complexity",
        "risky-hotspot",
    }
    return [finding for finding in issue_models if finding.rule in risk_rules]


def _dead_findings(issue_models: list[Finding]) -> list[Finding]:
    return [finding for finding in issue_models if finding.rule in {"unused-module", "unused-symbol"}]


def _dependency_findings(issue_models: list[Finding]) -> list[Finding]:
    dependency_rules = {rule for rule, meta in RULES.items() if meta["category"] == "dependencies"}
    return [finding for finding in issue_models if finding.rule in dependency_rules]


def _fan_lists(edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fan_in: dict[str, int] = {}
    fan_out: dict[str, int] = {}
    for edge in edges:
        fan_out[edge["from"]] = fan_out.get(edge["from"], 0) + 1
        fan_in[edge["to"]] = fan_in.get(edge["to"], 0) + 1
    return (_sorted_fan(fan_in), _sorted_fan(fan_out))


def _sorted_fan(counts: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"module": module, "count": count}
        for module, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _boundary_rules(root: str | Path) -> list[BoundaryRuleSummary]:
    config = load_config(root)
    return [
        BoundaryRuleSummary(
            name=rule.name,
            from_patterns=rule.from_patterns,
            disallow=rule.disallow,
            severity=rule.severity,
        )
        for rule in config.boundary_rules
    ]


def _risk_item(finding: Finding) -> RiskItem:
    return RiskItem(
        rule=finding.rule,
        severity=finding.severity,
        confidence=finding.confidence,
        path=finding.path,
        message=finding.message,
        fingerprint=finding.fingerprint,
    )
