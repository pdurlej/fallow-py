from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .models import RULES

DEFAULT_MAX_RELATED_LOCATIONS = 20


def to_sarif(result: dict[str, Any], max_related_locations: int = DEFAULT_MAX_RELATED_LOCATIONS) -> dict[str, Any]:
    used_rules = sorted({issue["rule"] for issue in result.get("issues", [])})
    indexes = {RULES[rule]["id"]: index for index, rule in enumerate(used_rules)}
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "automationDetails": {"id": "pyfallow/python/"},
                "tool": {
                    "driver": {
                        "name": "pyfallow",
                        "informationUri": "https://github.com/fallow-rs/fallow",
                        "semanticVersion": result.get("version", "0.1.0"),
                        "rules": [_sarif_rule(rule) for rule in used_rules],
                    }
                },
                "results": [_sarif_result(issue, indexes, max_related_locations) for issue in result.get("issues", [])],
            }
        ],
    }


def _sarif_rule(rule: str) -> dict[str, Any]:
    meta = RULES[rule]
    return {
        "id": meta["id"],
        "name": rule,
        "shortDescription": {"text": rule.replace("-", " ").title()},
        "fullDescription": {"text": f"pyfallow {rule} finding."},
        "defaultConfiguration": {"level": _level(meta["default_severity"])},
        "properties": {
            "category": meta["category"],
            "precision": meta["precision"],
            "problem.severity": _problem_severity(meta["default_severity"]),
        },
    }


def _sarif_result(issue: dict[str, Any], indexes: dict[str, int], max_related_locations: int) -> dict[str, Any]:
    region = issue.get("range", {}).get("start", {})
    end = issue.get("range", {}).get("end", {})
    path = issue.get("path") or "."
    result = {
        "ruleId": issue["id"],
        "ruleIndex": indexes.get(issue["id"], 0),
        "level": _level(issue["severity"]),
        "message": {"text": issue["message"]},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": path},
                    "region": {
                        "startLine": max(1, int(region.get("line", 1))),
                        "startColumn": max(1, int(region.get("column", 1))),
                        "endLine": max(1, int(end.get("line", region.get("line", 1)))),
                        "endColumn": max(1, int(end.get("column", region.get("column", 1)))),
                    },
                }
            }
        ],
        "partialFingerprints": {
            "pyfallowFingerprint": issue.get("fingerprint", ""),
            "primaryLocationLineHash": _line_hash(issue),
        },
        "properties": {
            "rule": issue["rule"],
            "confidence": issue["confidence"],
            "category": issue["category"],
        },
    }
    related = _related_locations(issue, max_related_locations)
    if related:
        result["relatedLocations"] = related
    return result


def _level(severity: str) -> str:
    return {"error": "error", "warning": "warning", "info": "note"}.get(severity, "warning")


def _problem_severity(severity: str) -> str:
    return {"error": "error", "warning": "warning", "info": "recommendation"}.get(severity, "warning")


def _line_hash(issue: dict[str, Any]) -> str:
    start = issue.get("range", {}).get("start", {})
    path = Path(issue.get("path") or ".")
    line_no = max(1, int(start.get("line", 1)))
    if path.exists() and path.is_file():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line_no <= len(lines):
                raw = " ".join(lines[line_no - 1].strip().split())
                return hashlib.sha1(raw.encode("utf-8")).hexdigest()
        except OSError:
            pass
    raw = f"{issue.get('path') or '.'}:{line_no}:{issue.get('rule')}:{issue.get('symbol') or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _related_locations(issue: dict[str, Any], max_related_locations: int) -> list[dict[str, Any]]:
    evidence = issue.get("evidence", {})
    locations: list[dict[str, Any]] = []
    limit = max(0, max_related_locations)
    if issue.get("rule") == "circular-dependency":
        for index, item in enumerate(evidence.get("import_lines", [])[:limit], start=1):
            locations.append(
                {
                    "id": index,
                    "message": {"text": f"Cycle edge {index}: {item.get('from')} imports {item.get('to')}"},
                    "physicalLocation": {
                        "artifactLocation": {"uri": item.get("path") or "."},
                        "region": {"startLine": max(1, int(item.get("line", 1)))},
                    },
                }
            )
    elif issue.get("rule") == "duplicate-code":
        fragments = evidence.get("fragments", [])
        for index, fragment in enumerate(fragments[:limit], start=1):
            start = fragment.get("range", {}).get("start", {})
            end = fragment.get("range", {}).get("end", {})
            locations.append(
                {
                    "id": index,
                    "message": {"text": f"Duplicate fragment {index} of {len(fragments)}"},
                    "physicalLocation": {
                        "artifactLocation": {"uri": fragment.get("path") or "."},
                        "region": {
                            "startLine": max(1, int(start.get("line", 1))),
                            "endLine": max(1, int(end.get("line", start.get("line", 1)))),
                        },
                    },
                }
            )
    return locations
