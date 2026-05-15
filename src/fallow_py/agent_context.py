from __future__ import annotations

from typing import Any


def agent_context_markdown(result: dict[str, Any]) -> str:
    analysis = result["analysis"]
    summary = result["summary"]
    metrics = result["metrics"]
    graphs = result["graphs"]
    issues = result["issues"]

    def by_rule(rule: str) -> list[dict[str, Any]]:
        return [issue for issue in issues if issue["rule"] == rule]

    top_hotspots = metrics.get("top_hotspots", [])[:10]
    cycles = graphs.get("cycles", [])[:10]
    edges = graphs.get("edges", [])
    fan_in: dict[str, int] = {}
    fan_out: dict[str, int] = {}
    for edge in edges:
        fan_out[edge["from"]] = fan_out.get(edge["from"], 0) + 1
        fan_in[edge["to"]] = fan_in.get(edge["to"], 0) + 1

    lines = [
        "# Fallow Python Agent Context",
        "",
        "## Project Overview",
        f"- Roots: {', '.join(analysis.get('source_roots', [])) or '.'}",
        f"- Entrypoints: {_join_entries(analysis.get('entrypoints', []))}",
        f"- Detected frameworks: {', '.join(analysis.get('frameworks_detected', [])) or 'none'}",
        f"- Dependency files: {', '.join(analysis.get('dependency_files', [])) or 'none'}",
        f"- Modules analyzed: {analysis.get('modules_analyzed', 0)}",
        "",
        "## Architecture Map",
        f"- High fan-in modules: {_top_counts(fan_in)}",
        f"- High fan-out modules: {_top_counts(fan_out)}",
        f"- Import cycles: {_cycle_summary(cycles)}",
        "",
        "## Risk Map",
        f"- Top hotspots: {_hotspot_summary(top_hotspots)}",
        f"- Boundary violations: {len(by_rule('boundary-violation'))}",
        f"- Duplicate groups: {summary.get('duplicate_groups', 0)}",
        f"- High complexity functions: {summary.get('complexity_hotspots', 0)}",
        "",
        "## Dead Code Candidates",
        f"- Unused modules: {_issue_summary(by_rule('unused-module'))}",
        f"- Unused symbols: {_issue_summary(by_rule('unused-symbol'))}",
        "",
        "## Dependency Findings",
        f"- Missing: {_issue_summary(_issues_by_rules(issues, {'missing-runtime-dependency', 'missing-type-dependency', 'missing-test-dependency'}))}",
        f"- Unused/scope: {_issue_summary(_issues_by_rules(issues, {'unused-runtime-dependency', 'runtime-dependency-used-only-in-tests', 'runtime-dependency-used-only-for-types'}))}",
        f"- Optional/dev concerns: {_issue_summary(_issues_by_rules(issues, {'optional-dependency-used-in-runtime', 'dev-dependency-used-in-runtime'}))}",
        "",
        "## Suggested Agent Workflow",
        "1. Fix parse errors and missing dependencies before trusting lower-confidence findings.",
        "2. Inspect boundary violations, cycles, and hotspots before broad edits.",
        "3. Review high-confidence dead modules first; avoid auto-deleting low-confidence framework modules.",
        "4. Rerun fallow-py after edits and compare against the baseline when one exists.",
        "",
        "## Limitations",
    ]
    lines.extend(f"- {item}" for item in result.get("limitations", []))
    return "\n".join(lines) + "\n"


def agent_context_json(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_overview": {
            "roots": result["analysis"].get("source_roots", []),
            "entrypoints": result["analysis"].get("entrypoints", []),
            "frameworks": result["analysis"].get("frameworks_detected", []),
            "dependency_files": result["analysis"].get("dependency_files", []),
            "modules": result["analysis"].get("modules_analyzed", 0),
        },
        "architecture_map": {
            "cycles": result["graphs"].get("cycles", [])[:20],
            "edges": result["graphs"].get("edges", [])[:200],
        },
        "risk_map": {
            "top_hotspots": result["metrics"].get("top_hotspots", []),
            "issues": [
                issue
                for issue in result["issues"]
                if issue["rule"] in {"boundary-violation", "duplicate-code", "high-cyclomatic-complexity", "high-cognitive-complexity", "risky-hotspot"}
            ][:100],
        },
        "dead_code_candidates": [
            issue for issue in result["issues"] if issue["rule"] in {"unused-module", "unused-symbol"}
        ][:100],
        "dependency_findings": [
            issue
            for issue in result["issues"]
            if issue["rule"] in {
                "missing-runtime-dependency",
                "missing-type-dependency",
                "missing-test-dependency",
                "unused-runtime-dependency",
                "runtime-dependency-used-only-in-tests",
                "runtime-dependency-used-only-for-types",
                "optional-dependency-used-in-runtime",
                "dev-dependency-used-in-runtime",
            }
        ][:100],
        "limitations": result.get("limitations", []),
    }


def _join_entries(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "none"
    return ", ".join(f"{entry['module']} ({entry['confidence']})" for entry in entries[:10])


def _top_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8])


def _cycle_summary(cycles: list[dict[str, Any]]) -> str:
    if not cycles:
        return "none"
    return "; ".join(" -> ".join(cycle["path"]) for cycle in cycles[:5])


def _hotspot_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "none"
    return ", ".join(f"{item['path']}={item['score']}" for item in items[:8])


def _issue_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "none"
    return ", ".join(f"{item.get('path')}:{item.get('symbol') or item.get('module') or item['rule']} ({item['confidence']})" for item in items[:8])


def _issues_by_rules(issues: list[dict[str, Any]], rules: set[str]) -> list[dict[str, Any]]:
    return [issue for issue in issues if issue["rule"] in rules]
