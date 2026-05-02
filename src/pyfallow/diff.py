from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import matches_any, relpath

GIT_TIMEOUT_SECONDS = 5


@dataclass(slots=True)
class DiffResolution:
    changed_files: list[str]
    since_resolved: str | None
    warning: dict[str, str] | None = None

    @property
    def filtering_active(self) -> bool:
        return self.warning is None


def resolve_since(root: Path, ref: str, ignore: list[str]) -> DiffResolution:
    repo_root_result = _git(root, "rev-parse", "--show-toplevel")
    if repo_root_result is None:
        return _unavailable(
            "since-not-available-non-git",
            "--since requested outside a Git workspace; full analysis was used.",
        )
    if repo_root_result.returncode != 0:
        return _unavailable(
            "since-not-available-non-git",
            "--since requested outside a Git workspace; full analysis was used.",
        )

    repo_root = Path(repo_root_result.stdout.strip()).resolve()
    resolved = _git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved is None:
        return _unavailable("since-not-available-non-git", "git executable was not available; full analysis was used.")
    if resolved.returncode != 0:
        raise ValueError(f"ref not found: {ref}")

    diff = _git(
        repo_root,
        "diff",
        "--name-only",
        "--find-renames",
        "--diff-filter=ACMR",
        f"{ref}...HEAD",
        "--",
    )
    if diff is None:
        return _unavailable("since-not-available-non-git", "git executable was not available; full analysis was used.")
    if diff.returncode != 0:
        detail = " ".join((diff.stderr or diff.stdout).strip().split())
        message = f"Could not compute git diff for --since {ref}; full analysis was used."
        if detail:
            message = f"{message} git said: {detail}"
        return _unavailable("since-not-available-git-error", message)

    changed_files = _changed_python_files(root.resolve(), repo_root, diff.stdout.splitlines(), ignore)
    return DiffResolution(changed_files=changed_files, since_resolved=resolved.stdout.strip())


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _changed_python_files(root: Path, repo_root: Path, paths: list[str], ignore: list[str]) -> list[str]:
    changed: set[str] = set()
    for raw in paths:
        repo_relative = raw.strip().replace("\\", "/")
        if not repo_relative:
            continue
        absolute = (repo_root / repo_relative).resolve()
        try:
            absolute.relative_to(root)
        except ValueError:
            continue
        analysis_relative = relpath(absolute, root)
        if analysis_relative.startswith("../") or analysis_relative == "..":
            continue
        if not analysis_relative.endswith(".py"):
            continue
        if matches_any(analysis_relative, ignore):
            continue
        changed.add(analysis_relative)
    return sorted(changed)


def _unavailable(code: str, message: str) -> DiffResolution:
    return DiffResolution(changed_files=[], since_resolved=None, warning={"code": code, "message": message})
