from __future__ import annotations

import hashlib
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PythonConfig
from .models import Action, Issue, ModuleInfo, Position, Range


@dataclass(slots=True)
class Fragment:
    path: str
    start_line: int
    end_line: int
    token_count: int
    line_count: int
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "range": {
                "start": {"line": self.start_line, "column": 1},
                "end": {"line": self.end_line, "column": 1},
            },
            "token_count": self.token_count,
            "line_count": self.line_count,
        }


def duplicate_issues(config: PythonConfig, modules: dict[str, ModuleInfo]) -> tuple[list[Issue], list[dict[str, Any]], set[str]]:
    if not config.dupes.enabled:
        return [], [], set()
    windows: dict[str, list[Fragment]] = {}
    for module in sorted(modules.values(), key=lambda item: item.path):
        if module.parse_error or module.is_generated:
            continue
        if module.is_test and not config.include_tests:
            continue
        try:
            text = (config.root / module.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tokens = _normalized_tokens(text, config.dupes.mode)
        step = max(1, config.dupes.min_tokens // 2)
        for start in range(0, max(0, len(tokens) - config.dupes.min_tokens + 1), step):
            window = tokens[start : start + config.dupes.min_tokens]
            start_line = window[0][1]
            end_line = window[-1][2]
            line_count = end_line - start_line + 1
            if line_count < config.dupes.min_lines:
                continue
            digest = hashlib.sha1(" ".join(token for token, _s, _e in window).encode("utf-8")).hexdigest()[:20]
            windows.setdefault(digest, []).append(
                Fragment(module.path, start_line, end_line, len(window), line_count, digest)
            )
    candidates: list[tuple[str, list[Fragment]]] = []
    for digest, fragments in sorted(windows.items()):
        selected = _dedupe_fragments(fragments)
        paths = {fragment.path for fragment in selected}
        if len(selected) < 2 or len(paths) < 2:
            continue
        selected = sorted(selected, key=lambda item: (item.path, item.start_line, item.end_line))
        candidates.append((digest, selected))

    groups: list[dict[str, Any]] = []
    involved: set[str] = set()
    occupied: dict[str, list[Fragment]] = {}
    reported_path_sets: set[tuple[str, ...]] = set()
    for digest, selected in sorted(
        candidates,
        key=lambda item: (-item[1][0].token_count, -item[1][0].line_count, item[1][0].path, item[1][0].start_line, item[0]),
    ):
        path_set = tuple(sorted({fragment.path for fragment in selected}))
        if path_set in reported_path_sets:
            continue
        if any(_overlaps(fragment, other) for fragment in selected for other in occupied.get(fragment.path, [])):
            continue
        reported_path_sets.add(path_set)
        involved.update(fragment.path for fragment in selected)
        for fragment in selected:
            occupied.setdefault(fragment.path, []).append(fragment)
        groups.append(
            {
                "hash": digest,
                "occurrences": len(selected),
                "fragments": [fragment.to_dict() for fragment in selected],
                "token_count": selected[0].token_count,
                "line_count": selected[0].line_count,
            }
        )
        if len(groups) >= config.dupes.max_groups:
            break
    issues: list[Issue] = []
    confidence = "high" if config.dupes.mode == "strict" else "medium"
    severity = "warning"
    for group in groups:
        first = group["fragments"][0]
        issues.append(
            Issue(
                rule="duplicate-code",
                severity=severity,
                confidence=confidence,
                path=first["path"],
                range=Range(
                    Position(first["range"]["start"]["line"], 1),
                    Position(first["range"]["end"]["line"], 1),
                ),
                message=f"Duplicate code block appears in {group['occurrences']} locations.",
                evidence={
                    "normalized_hash": group["hash"],
                    "mode": config.dupes.mode,
                    "fragments": group["fragments"],
                    "token_count": group["token_count"],
                    "line_count": group["line_count"],
                },
                actions=[
                    Action(
                        "review-deduplicate",
                        False,
                        "Extract shared behavior only if the duplicated blocks represent the same concept.",
                    )
                ],
            )
        )
    return issues, groups, involved


def _normalized_tokens(text: str, mode: str) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    stream = io.StringIO(text).readline
    previous_significant_line = 0
    try:
        for token in tokenize.generate_tokens(stream):
            token_type = token.type
            value = token.string
            if token_type in {
                tokenize.ENCODING,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.COMMENT,
                tokenize.ENDMARKER,
            }:
                continue
            if token_type == tokenize.STRING and token.start[0] == previous_significant_line + 1:
                # Module/function docstrings are hard to distinguish token-only;
                # treating standalone leading strings as ignorable lowers noise.
                previous_significant_line = token.start[0]
                continue
            previous_significant_line = token.start[0]
            if mode in {"mild", "structural"}:
                if token_type == tokenize.NAME and value not in PY_KEYWORDS:
                    value = "<ID>"
                elif token_type == tokenize.STRING:
                    value = "<STR>"
                elif token_type == tokenize.NUMBER:
                    value = "<NUM>"
            result.append((value, token.start[0], token.end[0]))
    except tokenize.TokenError:
        return result
    return result


def _dedupe_fragments(fragments: list[Fragment]) -> list[Fragment]:
    selected: list[Fragment] = []
    by_path: dict[str, list[Fragment]] = {}
    for fragment in sorted(fragments, key=lambda item: (item.path, item.start_line, item.end_line)):
        existing = by_path.setdefault(fragment.path, [])
        if any(_overlaps(fragment, other) for other in existing):
            continue
        existing.append(fragment)
        selected.append(fragment)
    return selected


def _overlaps(a: Fragment, b: Fragment) -> bool:
    return a.start_line <= b.end_line and b.start_line <= a.end_line


PY_KEYWORDS = {
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
}
