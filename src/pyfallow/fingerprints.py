from __future__ import annotations

import hashlib
import json

from .models import Issue, stable_data


def issue_fingerprint(issue: Issue) -> str:
    payload = {
        "rule": issue.rule,
        "path": issue.path,
        "symbol": issue.symbol,
        "module": issue.module,
        "target": issue.evidence.get("distribution")
        or issue.evidence.get("imported_module")
        or issue.evidence.get("normalized_hash")
        or issue.evidence.get("cycle_path")
        or issue.message.split(".", 1)[0],
    }
    raw = json.dumps(stable_data(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def assign_fingerprints(issues: list[Issue]) -> None:
    for issue in issues:
        if not issue.fingerprint:
            issue.fingerprint = issue_fingerprint(issue)
