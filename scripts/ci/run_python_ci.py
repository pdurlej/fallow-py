#!/usr/bin/env python3
"""Run fallow-py CI checks and produce agent-readable artifacts."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path


ARTIFACT_DIR = Path(os.environ.get("CI_ARTIFACT_DIR", "ci-artifacts"))


def run_step(name: str, command: list[str], env: dict[str, str] | None = None) -> dict:
    started = time.monotonic()
    log_path = ARTIFACT_DIR / f"{slug(name)}.log"
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=merged_env,
    )
    lines: list[str] = []
    assert proc.stdout is not None
    with log_path.open("w", encoding="utf-8") as log:
        for line in proc.stdout:
            print(line, end="")
            log.write(line)
            lines.append(line)
    rc = proc.wait()
    return {
        "name": name,
        "command": " ".join(shlex.quote(part) for part in command),
        "status": "success" if rc == 0 else "failure",
        "returncode": rc,
        "durationSeconds": round(time.monotonic() - started, 2),
        "log": str(log_path),
        "lastLines": [line.rstrip("\n") for line in lines[-40:]],
    }


def slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def write_feedback(report: dict) -> None:
    failed = [step for step in report["steps"] if step["status"] != "success"]
    if not failed:
        body = [
            "## CI feedback: python-ci passed",
            "",
            "All Python checks passed for this matrix job.",
        ]
        excerpt = ""
    else:
        first = failed[0]
        body = [
            "## CI feedback: python-ci failed",
            "",
            f"**Failed check:** {first['name']}",
            f"**Why:** command exited with `{first['returncode']}`.",
            "**Artifact to read:** `python-ci-*` -> `ci-report.json` and step logs.",
            "**Expected next action:** fix the failing command, then push a new commit to the same PR.",
            "",
            "```text",
            *first["lastLines"][-40:],
            "```",
        ]
        excerpt = "\n".join(first["lastLines"][-40:]) + "\n"
    (ARTIFACT_DIR / "ci-feedback.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    (ARTIFACT_DIR / "last-log-excerpt.txt").write_text(excerpt, encoding="utf-8")


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    env = {"PYTHONPATH": "src:mcp/src"}
    steps = [
        ("Install project", [py, "-m", "pip", "install", "--upgrade", "pip"]),
        ("Install package", [py, "-m", "pip", "install", "-e", ".[dev]"]),
        ("Compile", [py, "-m", "compileall", "-q", "src", "tests", "mcp/src", "mcp/tests"]),
        ("Test", [py, "-m", "pytest", "-q"]),
        ("Self audit", [py, "-m", "fallow_py", "analyze", "--root", ".", "--fail-on", "warning", "--min-confidence", "medium"]),
        ("CLI smoke json", [py, "-m", "fallow_py", "--format", "json", "--root", ".", "--output", str(ARTIFACT_DIR / "pyfallow-report.json")]),
        ("CLI smoke text", [py, "-m", "fallow_py", "analyze", "--format", "text", "--root", "."]),
        ("CLI smoke sarif", [py, "-m", "fallow_py", "analyze", "--format", "sarif", "--root", ".", "--output", str(ARTIFACT_DIR / "pyfallow.sarif")]),
        ("Agent context smoke", [py, "-m", "fallow_py", "agent-context", "--format", "markdown", "--root", ".", "--output", str(ARTIFACT_DIR / "pyfallow-agent-context.md")]),
        ("Baseline create", [py, "-m", "fallow_py", "baseline", "create", "--root", ".", "--output", str(ARTIFACT_DIR / "pyfallow-baseline.json")]),
        ("Baseline compare", [py, "-m", "fallow_py", "baseline", "compare", "--root", ".", "--baseline", str(ARTIFACT_DIR / "pyfallow-baseline.json")]),
        ("Legacy CLI smoke", [py, "-m", "pyfallow", "--version"]),
        ("Install MCP package", [py, "-m", "pip", "install", "-e", "./mcp"]),
        ("MCP tests", [py, "-m", "pytest", "-q", "mcp/tests"]),
        ("MCP self audit", [py, "-m", "fallow_py", "analyze", "--root", "mcp", "--fail-on", "warning", "--min-confidence", "medium"]),
        ("MCP smoke", [py, "-m", "fallow_py_mcp", "--help"]),
        ("Legacy MCP smoke", [py, "-m", "pyfallow_mcp", "--help"]),
        ("Build package", [py, "-m", "build"]),
        ("Check package", ["/bin/sh", "-lc", f"{shlex.quote(py)} -m twine check dist/*"]),
        (
            "Build MCP package",
            [
                "/bin/sh",
                "-lc",
                f"cd mcp && {shlex.quote(py)} -m build && {shlex.quote(py)} -m twine check dist/*",
            ],
        ),
    ]
    results = [run_step(name, command, env=env) for name, command in steps]
    exit_code = next((step["returncode"] for step in results if step["returncode"] != 0), 0)
    report = {
        "schema": "pyfallow_python_ci.v1",
        "python": sys.version,
        "matrixPythonVersion": os.environ.get("PYTHON_VERSION", ""),
        "status": "success" if exit_code == 0 else "failure",
        "exitCode": exit_code,
        "steps": results,
    }
    (ARTIFACT_DIR / "ci-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ARTIFACT_DIR / "ci-exit-code.txt").write_text(f"{exit_code}\n", encoding="utf-8")
    write_feedback(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
