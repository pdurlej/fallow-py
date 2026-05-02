from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOAK_DIR = Path(__file__).resolve().parent
DEFAULT_REPOS = SOAK_DIR / "repos.toml"
DEFAULT_MODELS = SOAK_DIR / "models.toml"
DEFAULT_WORKSPACE = SOAK_DIR / "workspace"
DEFAULT_RESULTS = SOAK_DIR / "results"
TIMEOUT_SECONDS = 1800


@dataclass(frozen=True, slots=True)
class Repo:
    name: str
    url: str
    commit: str
    since: str
    category: str
    notes: str


@dataclass(frozen=True, slots=True)
class Model:
    name: str
    provider: str
    model: str
    role: str
    notes: str


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repos = load_repos(args.repos_config)
    models = load_models(args.models_config)
    if args.list:
        print(json.dumps(matrix_summary(repos, models), indent=2, sort_keys=True))
        return 0

    selected_repos = select_items(repos, args.repo, "repo")
    selected_models = select_items(models, args.model, "model")
    for repo in selected_repos:
        for model in selected_models:
            run_one(repo, model, args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or plan pyfallow multi-model soak jobs.")
    parser.add_argument("--repos-config", type=Path, default=DEFAULT_REPOS)
    parser.add_argument("--models-config", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--repo", default="all", help="Repo name from repos.toml, or all.")
    parser.add_argument("--model", default="all", help="Model name from models.toml, or all.")
    parser.add_argument("--list", action="store_true", help="Print configured repo/model matrix as JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Write plan files without cloning or running tools.")
    parser.add_argument("--execute", action="store_true", help="Clone repos and run pyfallow/opencode commands.")
    parser.add_argument("--skip-opencode", action="store_true", help="Run pyfallow only, not opencode.")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SECONDS)
    return parser


def load_repos(path: Path) -> list[Repo]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [Repo(**item) for item in data.get("repos", [])]


def load_models(path: Path) -> list[Model]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [Model(**item) for item in data.get("models", [])]


def select_items(items: list[Any], name: str, label: str) -> list[Any]:
    if name == "all":
        return items
    selected = [item for item in items if item.name == name]
    if not selected:
        choices = ", ".join(item.name for item in items)
        raise SystemExit(f"Unknown {label} {name!r}; expected one of: {choices}")
    return selected


def matrix_summary(repos: list[Repo], models: list[Model]) -> dict[str, Any]:
    return {
        "repos": [asdict(repo) for repo in repos],
        "models": [asdict(model) for model in models],
        "planned_runs": len(repos) * len(models),
    }


def run_one(repo: Repo, model: Model, args: argparse.Namespace) -> None:
    result_dir = args.results / repo.name / model.name
    repo_dir = args.workspace / repo.name
    result_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(repo, model, repo_dir, result_dir)
    write_json(result_dir / "plan.json", plan)
    write_classification_template(result_dir / "human_classification.md", repo, model)
    if args.dry_run or not args.execute:
        return

    started = time.time()
    clone_or_checkout(repo, repo_dir, args.timeout)
    pyfallow_result = run_command(plan["commands"]["pyfallow"], result_dir / "pyfallow.stderr", args.timeout)
    opencode_result: dict[str, Any] | None = None
    if not args.skip_opencode:
        opencode_result = run_opencode(plan, result_dir, args.timeout)
    write_json(
        result_dir / "time.json",
        {
            "started_at": started,
            "ended_at": time.time(),
            "duration_seconds": round(time.time() - started, 3),
            "pyfallow": pyfallow_result,
            "opencode": opencode_result,
        },
    )


def build_plan(repo: Repo, model: Model, repo_dir: Path, result_dir: Path) -> dict[str, Any]:
    prompt = (
        "Use pyfallow MCP tools and the generated agent-fix-plan output to inspect the last "
        f"change window for {repo.name}. Group findings by auto_safe, review_needed, "
        "blocking, and manual_only. Do not invent findings that are not present in pyfallow output."
    )
    return {
        "repo": asdict(repo),
        "model": asdict(model),
        "paths": {
            "repo_dir": str(repo_dir),
            "result_dir": str(result_dir),
            "findings": str(result_dir / "findings.json"),
        },
        "commands": {
            "clone": ["git", "clone", "--no-checkout", repo.url, str(repo_dir)],
            "checkout": ["git", "-C", str(repo_dir), "checkout", repo.commit],
            "pyfallow": [
                sys.executable,
                "-m",
                "pyfallow",
                "analyze",
                "--root",
                str(repo_dir),
                "--since",
                repo.since,
                "--format",
                "agent-fix-plan",
                "--output",
                str(result_dir / "findings.json"),
            ],
            "opencode": ["opencode", "--model", model.model, prompt],
        },
    }


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


def run_opencode(plan: dict[str, Any], result_dir: Path, timeout: int) -> dict[str, Any]:
    if not shutil.which("opencode"):
        return {"skipped": True, "reason": "opencode executable not found"}
    output_path = result_dir / "agent_output.md"
    result = run_command(plan["commands"]["opencode"], result_dir / "opencode.stderr", timeout)
    output_path.write_text(result.pop("stdout", ""), encoding="utf-8")
    return result


def run_command(command: list[str], stderr_path: Path | None, timeout: int) -> dict[str, Any]:
    started = time.time()
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
        "duration_seconds": round(time.time() - started, 3),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def require_success(result: dict[str, Any], label: str) -> None:
    if result["returncode"] != 0:
        raise SystemExit(f"{label} failed with exit code {result['returncode']}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_classification_template(path: Path, repo: Repo, model: Model) -> None:
    if path.exists():
        return
    path.write_text(
        "\n".join(
            [
                f"# Human Classification: {repo.name} / {model.name}",
                "",
                "| fingerprint | rule | verdict | notes |",
                "| --- | --- | --- | --- |",
                "| TBD | TBD | true-positive / false-positive / disputed | TBD |",
                "",
                "Use `findings.json` as the source of truth. Do not classify model-invented findings.",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
