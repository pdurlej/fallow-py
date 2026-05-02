from __future__ import annotations

import json
from typing import Any

from .agent_context import agent_context_json, agent_context_markdown
from .sarif import to_sarif


def format_result(result: dict[str, Any], output_format: str, command: str = "analyze") -> str:
    if output_format == "json":
        return json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output_format == "sarif":
        return json.dumps(to_sarif(result), indent=2, sort_keys=True) + "\n"
    if output_format == "markdown":
        if command == "agent-context":
            return agent_context_markdown(result)
        return _markdown_report(result)
    return _text_report(result)


def format_agent_context(result: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(agent_context_json(result), indent=2, sort_keys=True) + "\n"
    return agent_context_markdown(result)


def _text_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    analysis = result["analysis"]
    lines = [
        f"pyfallow {result['version']} - {summary['total_issues']} issues "
        f"({summary['errors']} error, {summary['warnings']} warning, {summary['info']} info)",
        f"Analyzed {analysis['modules_analyzed']} modules / {analysis['files_analyzed']} files.",
    ]
    if analysis.get("entrypoints"):
        lines.append("Entrypoints: " + ", ".join(entry["module"] for entry in analysis["entrypoints"]))
    if analysis.get("frameworks_detected"):
        lines.append("Frameworks: " + ", ".join(analysis["frameworks_detected"]))
    for warning in analysis.get("warnings", []):
        lines.append(f"Warning: {warning.get('message', warning)}")
    if not result["issues"]:
        lines.append("No findings matched the active thresholds.")
    else:
        for issue in result["issues"][:200]:
            path = issue.get("path") or "."
            line = issue.get("range", {}).get("start", {}).get("line", 1)
            symbol = f" {issue['symbol']}" if issue.get("symbol") else ""
            lines.append(
                f"{path}:{line}: {issue['id']} {issue['severity']} {issue['confidence']} "
                f"{issue['rule']}{symbol} - {issue['message']}"
            )
        if len(result["issues"]) > 200:
            lines.append(f"... {len(result['issues']) - 200} more findings omitted from text output.")
    if not result.get("config", {}).get("boundary_rules_configured", False):
        lines.append("Boundary rules: none configured.")
    return "\n".join(lines) + "\n"


def _markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# pyfallow Report",
        "",
        f"- Issues: {result['summary']['total_issues']}",
        f"- Modules: {result['analysis']['modules_analyzed']}",
        f"- Frameworks: {', '.join(result['analysis'].get('frameworks_detected', [])) or 'none'}",
        "",
        "## Findings",
    ]
    for issue in result["issues"][:200]:
        lines.append(
            f"- `{issue['id']}` `{issue['severity']}` `{issue['confidence']}` "
            f"{issue.get('path') or '.'}:{issue['range']['start']['line']} - {issue['message']}"
        )
    if not result["issues"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"
