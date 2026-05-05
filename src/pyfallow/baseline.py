from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ConfigError
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
    baseline_path = Path(path)
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Baseline file {baseline_path} is not valid JSON: {exc}") from exc
    _validate_baseline_shape(data, baseline_path)
    if "issues" not in data and "fingerprints" in data:
        data["issues"] = [{"fingerprint": fingerprint} for fingerprint in data["fingerprints"]]
    return data


def _validate_baseline_shape(data: Any, path: Path) -> None:
    if not isinstance(data, dict):
        raise ConfigError(
            f"Baseline file {path} must contain a JSON object at top level, "
            f"got {type(data).__name__}"
        )
    if "version" not in data:
        raise ConfigError(f"Baseline file {path} missing required field 'version'")
    if not isinstance(data["version"], str):
        raise ConfigError(
            f"Baseline file {path} field 'version' must be a string, "
            f"got {type(data['version']).__name__}"
        )
    if "issues" in data:
        _validate_issue_fingerprints(data["issues"], path)
        return
    if "fingerprints" in data:
        _validate_legacy_fingerprints(data["fingerprints"], path)
        return
    raise ConfigError(f"Baseline file {path} missing required field 'issues'")


def _validate_issue_fingerprints(value: Any, path: Path) -> None:
    if not isinstance(value, list):
        raise ConfigError(
            f"Baseline file {path} field 'issues' must be a list, got {type(value).__name__}"
        )
    bad_indices = [
        index
        for index, issue in enumerate(value)
        if not isinstance(issue, dict) or not isinstance(issue.get("fingerprint"), str)
    ]
    if bad_indices:
        raise ConfigError(
            f"Baseline file {path} field 'issues' must contain objects with string "
            f"'fingerprint' values; invalid entries at indices {_index_sample(bad_indices)}"
        )


def _validate_legacy_fingerprints(value: Any, path: Path) -> None:
    if not isinstance(value, list):
        raise ConfigError(
            f"Baseline file {path} field 'fingerprints' must be a list, got {type(value).__name__}"
        )
    bad_indices = [index for index, fingerprint in enumerate(value) if not isinstance(fingerprint, str)]
    if bad_indices:
        raise ConfigError(
            f"Baseline file {path} field 'fingerprints' must contain only strings; "
            f"non-string values at indices {_index_sample(bad_indices)}"
        )


def _index_sample(indices: list[int]) -> str:
    suffix = "..." if len(indices) > 5 else ""
    return f"{indices[:5]}{suffix}"


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
