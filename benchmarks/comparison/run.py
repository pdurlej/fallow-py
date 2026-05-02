from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


BENCH_DIR = Path(__file__).resolve().parent
ROOT = BENCH_DIR.parents[1]
DEFAULT_REPOS = BENCH_DIR / "repos.toml"
DEFAULT_TOOLS = BENCH_DIR / "tools.toml"
DEFAULT_WORKSPACE = BENCH_DIR / "workspace"
DEFAULT_RESULTS = BENCH_DIR / "results"
DEFAULT_VENVS = BENCH_DIR / "venvs"
TIMEOUT_SECONDS = 1800


@dataclass(frozen=True, slots=True)
class Repo:
    name: str
    url: str
    commit: str
    since: str
    category: str


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    package: str
    version: str
    best_at: str


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repos = load_repos(args.repos_config)
    tools = load_tools(args.tools_config)
    if args.list:
        print(json.dumps(matrix_summary(repos, tools), indent=2, sort_keys=True))
        return 0

    selected_repos = select_items(repos, args.repo, "repo")
    selected_tools = select_items(tools, args.tool, "tool")
    for tool in selected_tools:
        if args.execute and not args.skip_install:
            ensure_tool(tool, args.venvs, args.timeout)
    for repo in selected_repos:
        if args.execute:
            clone_or_checkout(repo, args.workspace / repo.name, args.timeout)
        for tool in selected_tools:
            run_one(repo, tool, args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run complementary stack benchmarks.")
    parser.add_argument("--repos-config", type=Path, default=DEFAULT_REPOS)
    parser.add_argument("--tools-config", type=Path, default=DEFAULT_TOOLS)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--venvs", type=Path, default=DEFAULT_VENVS)
    parser.add_argument("--repo", default="all", help="Repo name from repos.toml, or all.")
    parser.add_argument("--tool", default="all", help="Tool name from tools.toml, or all.")
    parser.add_argument("--runs", type=int, default=5, help="Number of timed runs per repo/tool.")
    parser.add_argument("--list", action="store_true", help="Print configured repo/tool matrix as JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Write plan files without cloning/running.")
    parser.add_argument("--execute", action="store_true", help="Clone repos and run benchmark commands.")
    parser.add_argument("--skip-install", action="store_true", help="Use existing venv/tool binaries.")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SECONDS)
    return parser


def load_repos(path: Path) -> list[Repo]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [Repo(**item) for item in data.get("repos", [])]


def load_tools(path: Path) -> list[Tool]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [Tool(**item) for item in data.get("tools", [])]


def select_items(items: list[Any], name: str, label: str) -> list[Any]:
    if name == "all":
        return items
    selected = [item for item in items if item.name == name]
    if not selected:
        choices = ", ".join(item.name for item in items)
        raise SystemExit(f"Unknown {label} {name!r}; expected one of: {choices}")
    return selected


def matrix_summary(repos: list[Repo], tools: list[Tool]) -> dict[str, Any]:
    return {
        "repos": [asdict(repo) for repo in repos],
        "tools": [asdict(tool) for tool in tools],
        "planned_runs": len(repos) * len(tools),
        "timed_runs_per_pair": 5,
    }


def ensure_tool(tool: Tool, venvs: Path, timeout: int) -> None:
    venv_dir = venvs / tool.name
    python = venv_dir / "bin/python"
    if not python.exists():
        require_success(run_command([sys.executable, "-m", "venv", str(venv_dir)], None, timeout), "venv")
        require_success(
            run_command([str(python), "-m", "pip", "install", "--upgrade", "pip"], None, timeout),
            f"{tool.name} pip upgrade",
        )
    package_args = [tool.package]
    if tool.name == "pyfallow":
        package_args = ["-e", str(ROOT)]
    require_success(
        run_command([str(python), "-m", "pip", "install", *package_args], None, timeout),
        f"{tool.name} install",
    )


def clone_or_checkout(repo: Repo, repo_dir: Path, timeout: int) -> None:
    if not repo_dir.exists():
        require_success(
            run_command(["git", "clone", "--no-checkout", repo.url, str(repo_dir)], None, timeout),
            "git clone",
        )
    require_success(
        run_command(["git", "-C", str(repo_dir), "fetch", "--tags", "origin"], None, timeout),
        "git fetch",
    )
    require_success(
        run_command(["git", "-C", str(repo_dir), "checkout", repo.commit], None, timeout),
        "git checkout",
    )


def run_one(repo: Repo, tool: Tool, args: argparse.Namespace) -> None:
    repo_dir = args.workspace / repo.name
    result_dir = args.results / repo.name
    result_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(repo, tool, repo_dir, result_dir, args.venvs)
    write_json(result_dir / f"{tool.name}.plan.json", plan)
    if args.dry_run or not args.execute:
        return

    raw_dir = result_dir / "raw" / tool.name
    raw_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    last_result: dict[str, Any] | None = None
    for index in range(args.runs):
        clear_tool_caches(repo_dir)
        output_path = raw_dir / f"run-{index + 1}.json"
        command = command_for(tool, repo_dir, output_path, args.venvs)
        result = run_command(command, raw_dir / f"run-{index + 1}.stderr", args.timeout)
        output = result.pop("stdout", "")
        if output:
            (raw_dir / f"run-{index + 1}.stdout").write_text(output, encoding="utf-8")
        result["output_path"] = str(output_path) if output_path.exists() else None
        runs.append(result)
        last_result = result
    durations = [run["duration_seconds"] for run in runs]
    summary = summarize_tool_output(tool, runs, raw_dir)
    write_json(
        result_dir / f"{tool.name}.json",
        {
            "repo": asdict(repo),
            "tool": asdict(tool),
            "runs": runs,
            "median_seconds": round(statistics.median(durations), 4) if durations else None,
            "finding_count": summary["finding_count"],
            "coverage": summary["coverage"],
            "last_returncode": last_result["returncode"] if last_result else None,
        },
    )


def build_plan(repo: Repo, tool: Tool, repo_dir: Path, result_dir: Path, venvs: Path) -> dict[str, Any]:
    return {
        "repo": asdict(repo),
        "tool": asdict(tool),
        "repo_dir": str(repo_dir),
        "result_dir": str(result_dir),
        "command": command_for(tool, repo_dir, result_dir / "raw" / tool.name / "run-1.json", venvs),
    }


def command_for(tool: Tool, repo_dir: Path, output_path: Path, venvs: Path) -> list[str]:
    bin_dir = venvs / tool.name / "bin"
    if tool.name == "ruff":
        return [str(bin_dir / "ruff"), "check", str(repo_dir), "--output-format", "json", "--exit-zero"]
    if tool.name == "vulture":
        return [str(bin_dir / "vulture"), str(repo_dir)]
    if tool.name == "deptry":
        return [str(bin_dir / "deptry"), str(repo_dir), "--no-ansi", "-o", str(output_path)]
    if tool.name == "pyfallow":
        return [
            str(bin_dir / "python"),
            "-m",
            "pyfallow",
            "analyze",
            "--root",
            str(repo_dir),
            "--format",
            "json",
            "--output",
            str(output_path),
        ]
    raise SystemExit(f"Unsupported tool {tool.name!r}")


def summarize_tool_output(tool: Tool, runs: list[dict[str, Any]], raw_dir: Path) -> dict[str, Any]:
    if not runs:
        return empty_summary()
    last_index = len(runs)
    stdout_path = raw_dir / f"run-{last_index}.stdout"
    output_path = runs[-1].get("output_path")
    if tool.name == "ruff":
        findings = json.loads(stdout_path.read_text(encoding="utf-8") or "[]") if stdout_path.exists() else []
        return {"finding_count": len(findings), "coverage": coverage(style=len(findings))}
    if tool.name == "vulture":
        lines = [
            line
            for line in stdout_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("Scanning:")
        ] if stdout_path.exists() else []
        return {"finding_count": len(lines), "coverage": coverage(dead_code=len(lines))}
    if tool.name == "deptry" and output_path:
        findings = json.loads(Path(output_path).read_text(encoding="utf-8")) if Path(output_path).exists() else []
        return {"finding_count": len(findings), "coverage": coverage(dependencies=len(findings))}
    if tool.name == "pyfallow" and output_path:
        report = json.loads(Path(output_path).read_text(encoding="utf-8")) if Path(output_path).exists() else {}
        issues = report.get("issues", [])
        return {"finding_count": len(issues), "coverage": pyfallow_coverage(issues)}
    return empty_summary()


def clear_tool_caches(repo_dir: Path) -> None:
    for name in [".ruff_cache", ".mypy_cache", ".pytest_cache", ".deptry_cache"]:
        path = repo_dir / name
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def pyfallow_coverage(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = coverage()
    for issue in issues:
        rule = issue.get("rule", "")
        if rule in {"unused-module", "unused-symbol"}:
            counts["dead_code"] += 1
        elif "dependency" in rule:
            counts["dependencies"] += 1
        elif rule == "circular-dependency":
            counts["cycles"] += 1
        elif rule == "boundary-violation":
            counts["boundaries"] += 1
    return counts


def coverage(
    style: int = 0,
    dead_code: int = 0,
    dependencies: int = 0,
    cycles: int = 0,
    boundaries: int = 0,
) -> dict[str, int]:
    return {
        "style": style,
        "dead_code": dead_code,
        "dependencies": dependencies,
        "cycles": cycles,
        "boundaries": boundaries,
    }


def empty_summary() -> dict[str, Any]:
    return {"finding_count": 0, "coverage": coverage()}


def run_command(command: list[str], stderr_path: Path | None, timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if stderr_path:
        stderr_path.write_text(result.stderr, encoding="utf-8")
    return {
        "command": command,
        "returncode": result.returncode,
        "duration_seconds": round(time.perf_counter() - started, 4),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def require_success(result: dict[str, Any], label: str) -> None:
    if result["returncode"] != 0:
        raise SystemExit(f"{label} failed with exit code {result['returncode']}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
