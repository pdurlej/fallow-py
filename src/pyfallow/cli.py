from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .analysis import analyze, filter_result
from .baseline import compare_with_baseline, create_baseline, read_baseline, write_baseline
from .config import load_config
from .formatters import format_agent_context, format_result
from .models import CONFIDENCE_ORDER, SEVERITY_ORDER


COMMANDS = {
    "analyze",
    "dead-code",
    "deps",
    "graph",
    "cycles",
    "dupes",
    "health",
    "boundaries",
    "baseline",
    "agent-context",
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "python":
        argv = argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["analyze", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "baseline":
            return _run_baseline(args)
        return _run_analysis(args)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        if not getattr(args, "quiet", False):
            print(f"pyfallow error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyfallow", description="Python static codebase intelligence.")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["analyze", "dead-code", "deps", "graph", "cycles", "dupes", "health", "boundaries", "agent-context"]:
        child = sub.add_parser(command)
        _add_common(child, agent_context=command == "agent-context", graph=command == "graph")
        if command == "analyze":
            child.add_argument("--language", choices=["python"], default="python")
    baseline = sub.add_parser("baseline")
    baseline_sub = baseline.add_subparsers(dest="baseline_command", required=True)
    create = baseline_sub.add_parser("create")
    _add_common(create)
    compare = baseline_sub.add_parser("compare")
    _add_common(compare)
    return parser


def _add_common(parser: argparse.ArgumentParser, agent_context: bool = False, graph: bool = False) -> None:
    parser.add_argument("--root", default=".")
    parser.add_argument("--config")
    parser.add_argument(
        "--format",
        choices=["text", "json", "sarif", "markdown", "mermaid", "dot"],
        default="markdown" if agent_context else "text",
    )
    parser.add_argument("--output")
    tests = parser.add_mutually_exclusive_group()
    tests.add_argument("--include-tests", action="store_true")
    tests.add_argument("--exclude-tests", action="store_true")
    parser.add_argument("--changed-only", action="store_true")
    parser.add_argument("--baseline")
    parser.add_argument("--fail-on", choices=["none", "error", "warning", "any"], default="none")
    parser.add_argument("--min-confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--severity-threshold", choices=["info", "warning", "error"], default="info")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-framework-heuristics", action="store_true")
    parser.add_argument(
        "--framework",
        choices=["auto", "django", "fastapi", "flask", "celery", "pytest", "click", "typer", "none"],
        default="auto",
    )
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--show-limitations", action="store_true")


def _run_analysis(args: argparse.Namespace) -> int:
    config = load_config(args.root, args.config)
    _apply_cli_config(config, args)
    result = analyze(config)
    baseline = None
    if getattr(args, "baseline", None):
        baseline = read_baseline(args.baseline)
        comparison = compare_with_baseline(_issues_as_objects(result["issues"]), baseline)
        _mark_baseline_status(result, comparison)
        result["baseline"] = comparison
    filtered = filter_result(result, args.min_confidence, args.severity_threshold)
    output = _format_for_command(filtered, args.command, args.format)
    _write_or_print(output, args.output)
    exit_result = (
        _focused_result(filtered, args.command)
        if args.command in {"cycles", "dupes", "deps", "dead-code", "health", "boundaries"}
        else filtered
    )
    return _exit_code(exit_result, args.fail_on, baseline_active=baseline is not None)


def _run_baseline(args: argparse.Namespace) -> int:
    config = load_config(args.root, args.config)
    _apply_cli_config(config, args)
    result = analyze(config)
    if args.baseline_command == "create":
        baseline = create_baseline(result)
        output_path = args.output or config.baseline.path
        write_baseline(output_path, baseline)
        if not args.quiet:
            print(f"Wrote baseline with {baseline['summary']['total_issues']} issues to {output_path}")
        return 0
    baseline_path = args.baseline or config.baseline.path
    baseline = read_baseline(baseline_path)
    comparison = compare_with_baseline(_issues_as_objects(result["issues"]), baseline)
    _mark_baseline_status(result, comparison)
    result["baseline"] = comparison
    filtered = filter_result(result, args.min_confidence, args.severity_threshold)
    output = format_result(filtered, args.format, "baseline")
    _write_or_print(output, args.output)
    return _exit_code(filtered, args.fail_on, baseline_active=True)


def _apply_cli_config(config, args: argparse.Namespace) -> None:
    if args.include_tests:
        config.include_tests = True
    if args.exclude_tests:
        config.include_tests = False
    if args.no_framework_heuristics or args.framework == "none":
        config.framework_heuristics = False
    elif args.framework != "auto":
        config.frameworks = [args.framework]
    if args.changed_only:
        config.changed_only_requested = True
        if not _inside_git_workspace(config.root):
            config.changed_only_effective = False
            config.analysis_warnings.append(
                {
                    "code": "changed-only-unavailable",
                    "message": "--changed-only requested outside a Git workspace; full analysis was used.",
                }
            )
        else:
            config.changed_only_effective = False
            config.analysis_warnings.append(
                {
                    "code": "changed-only-not-implemented",
                    "message": "--changed-only is not implemented in this standalone backend yet; full analysis was used.",
                }
            )


def _inside_git_workspace(root: Path) -> bool:
    current = root.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return True
    return False


def _format_for_command(result: dict[str, Any], command: str, fmt: str) -> str:
    if command == "agent-context":
        return format_agent_context(result, "json" if fmt == "json" else "markdown")
    if command == "graph" and fmt in {"mermaid", "dot"}:
        return _graph_format(result, fmt)
    if command in {"cycles", "dupes", "deps", "dead-code", "health", "boundaries"}:
        focused = _focused_result(result, command)
        if fmt == "json":
            return json.dumps(focused, indent=2, sort_keys=True) + "\n"
        return format_result(focused, fmt, command)
    return format_result(result, fmt, command)


def _focused_result(result: dict[str, Any], command: str) -> dict[str, Any]:
    rules = {
        "cycles": {"circular-dependency"},
        "dupes": {"duplicate-code"},
        "deps": {
            "missing-runtime-dependency",
            "missing-type-dependency",
            "missing-test-dependency",
            "dev-dependency-used-in-runtime",
            "optional-dependency-used-in-runtime",
            "runtime-dependency-used-only-in-tests",
            "runtime-dependency-used-only-for-types",
            "unused-runtime-dependency",
        },
        "dead-code": {"unused-module", "unused-symbol", "stale-suppression"},
        "health": {
            "high-cyclomatic-complexity",
            "high-cognitive-complexity",
            "large-function",
            "large-file",
            "risky-hotspot",
        },
        "boundaries": {"boundary-violation"},
    }[command]
    clone = dict(result)
    clone["issues"] = [issue for issue in result["issues"] if issue["rule"] in rules]
    clone["summary"] = _simple_summary(clone["issues"], result["summary"].get("duplicate_groups", 0) if command == "dupes" else 0)
    return clone


def _simple_summary(issues: list[dict[str, Any]], duplicate_groups: int) -> dict[str, int]:
    summary = {
        "total_issues": len(issues),
        "errors": 0,
        "warnings": 0,
        "info": 0,
        "parse_errors": 0,
        "config_errors": 0,
        "unused_modules": 0,
        "unused_symbols": 0,
        "missing_dependencies": 0,
        "unused_dependencies": 0,
        "circular_dependencies": 0,
        "duplicate_groups": duplicate_groups,
        "complexity_hotspots": 0,
        "boundary_violations": 0,
        "stale_suppressions": 0,
    }
    for issue in issues:
        summary["errors" if issue["severity"] == "error" else "warnings" if issue["severity"] == "warning" else "info"] += 1
        if issue["rule"] == "unused-module":
            summary["unused_modules"] += 1
        elif issue["rule"] == "config-error":
            summary["config_errors"] += 1
        elif issue["rule"] == "unused-symbol":
            summary["unused_symbols"] += 1
        elif issue["rule"] in {
            "missing-runtime-dependency",
            "missing-type-dependency",
            "missing-test-dependency",
            "dev-dependency-used-in-runtime",
            "optional-dependency-used-in-runtime",
        }:
            summary["missing_dependencies"] += 1
        elif issue["rule"] in {
            "runtime-dependency-used-only-in-tests",
            "runtime-dependency-used-only-for-types",
            "unused-runtime-dependency",
        }:
            summary["unused_dependencies"] += 1
        elif issue["rule"] == "circular-dependency":
            summary["circular_dependencies"] += 1
        elif issue["rule"] == "boundary-violation":
            summary["boundary_violations"] += 1
        elif issue["rule"] == "stale-suppression":
            summary["stale_suppressions"] += 1
        elif issue["rule"].startswith("high-") or issue["rule"].startswith("large-") or issue["rule"] == "risky-hotspot":
            summary["complexity_hotspots"] += 1
    return summary


def _graph_format(result: dict[str, Any], fmt: str) -> str:
    edges = result["graphs"]["edges"]
    if fmt == "dot":
        lines = ["digraph pyfallow {"]
        for edge in edges:
            lines.append(f'  "{edge["from"]}" -> "{edge["to"]}";')
        lines.append("}")
        return "\n".join(lines) + "\n"
    lines = ["graph TD"]
    if not edges:
        lines.append("  empty[No local import edges]")
    for edge in edges:
        lines.append(f'  {edge["from"].replace(".", "_")}["{edge["from"]}"] --> {edge["to"].replace(".", "_")}["{edge["to"]}"]')
    return "\n".join(lines) + "\n"


def _write_or_print(output: str, path: str | None) -> None:
    if path:
        Path(path).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def _exit_code(result: dict[str, Any], fail_on: str, baseline_active: bool) -> int:
    if result["summary"].get("parse_errors", 0) and result["analysis"].get("modules_analyzed", 0) == result["summary"]["parse_errors"]:
        return 3
    if fail_on == "none":
        return 0
    issues = result["issues"]
    if baseline_active:
        issues = [issue for issue in issues if issue.get("baseline_status") == "new"]
    if fail_on == "any":
        return 1 if issues else 0
    threshold = {"error": "error", "warning": "warning"}[fail_on]
    return 1 if any(SEVERITY_ORDER[issue["severity"]] >= SEVERITY_ORDER[threshold] for issue in issues) else 0


def _issues_as_objects(issue_dicts: list[dict[str, Any]]):
    class IssueLike:
        def __init__(self, data: dict[str, Any]) -> None:
            self.fingerprint = data["fingerprint"]

    return [IssueLike(item) for item in issue_dicts]


def _mark_baseline_status(result: dict[str, Any], comparison: dict[str, Any]) -> None:
    new = set(comparison["new"])
    existing = set(comparison["existing"])
    for issue in result["issues"]:
        if issue["fingerprint"] in new:
            issue["baseline_status"] = "new"
        elif issue["fingerprint"] in existing:
            issue["baseline_status"] = "existing"


if __name__ == "__main__":
    raise SystemExit(main())
