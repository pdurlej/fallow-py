from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Issue, SCHEMA_VERSION, VERSION


def create_baseline(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": "fallow",
        "language": "python",
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "root": result.get("root", "."),
        "created_at": None,
        "issues": [
            {
                "fingerprint": issue["fingerprint"],
                "rule": issue["rule"],
                "path": issue.get("path"),
                "symbol": issue.get("symbol"),
                "severity": issue["severity"],
                "confidence": issue["confidence"],
            }
            for issue in result.get("issues", [])
        ],
        "summary": {"total_issues": len(result.get("issues", []))},
    }


def write_baseline(path: str | Path, baseline: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_baseline(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_with_baseline(issues: list[Issue], baseline: dict[str, Any]) -> dict[str, Any]:
    baseline_fps = {item["fingerprint"] for item in baseline.get("issues", [])}
    current_fps = {issue.fingerprint for issue in issues}
    new = [issue.fingerprint for issue in issues if issue.fingerprint not in baseline_fps]
    existing = [issue.fingerprint for issue in issues if issue.fingerprint in baseline_fps]
    resolved = sorted(baseline_fps - current_fps)
    return {
        "new": sorted(new),
        "existing": sorted(existing),
        "resolved": resolved,
        "new_count": len(new),
        "existing_count": len(existing),
        "resolved_count": len(resolved),
    }
