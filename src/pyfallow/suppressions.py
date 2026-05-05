from __future__ import annotations

import re

from .models import Issue, Position, Range, Suppression

SUPPRESSION_RE = re.compile(
    r"#\s*(?:fallow|pyfallow):\s*(?P<kind>ignore(?:\[(?P<rule>[a-z0-9_-]+)\])?|expected-unused)"
)

EXPECTED_UNUSED_RULES = {"unused-module", "unused-symbol"}
ALIASES = {
    "high-complexity": {
        "high-cyclomatic-complexity",
        "high-cognitive-complexity",
        "large-function",
        "large-file",
        "risky-hotspot",
    },
    "missing-dependency": {
        "missing-runtime-dependency",
        "missing-type-dependency",
        "missing-test-dependency",
        "dev-dependency-used-in-runtime",
    },
    "unused-dependency": {
        "unused-runtime-dependency",
        "runtime-dependency-used-only-in-tests",
        "runtime-dependency-used-only-for-types",
    },
    "undeclared-optional-dependency": {"optional-dependency-used-in-runtime"},
}


def parse_suppressions(path: str, lines: list[str]) -> list[Suppression]:
    suppressions: list[Suppression] = []
    logical = 0
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            logical += 1
        match = SUPPRESSION_RE.search(line)
        if not match:
            continue
        kind = match.group("kind")
        rule = match.group("rule")
        if kind == "expected-unused":
            rule = None
        suppressions.append(
            Suppression(
                path=path,
                line=index,
                rule=rule,
                raw=match.group(0),
                line_text=line.rstrip("\n"),
                file_wide=stripped.startswith("#") and logical <= 10 and index <= 20,
            )
        )
    return suppressions


def apply_suppressions(issues: list[Issue], suppressions: list[Suppression]) -> tuple[list[Issue], list[Issue]]:
    active: list[Issue] = []
    for issue in issues:
        matched = False
        for suppression in suppressions:
            if _applies(suppression, issue):
                suppression.used = True
                matched = True
                break
        if not matched:
            active.append(issue)

    stale: list[Issue] = []
    for suppression in suppressions:
        if suppression.used:
            continue
        rule = suppression.rule or "all"
        stale.append(
            Issue(
                rule="stale-suppression",
                severity="info",
                confidence="high",
                path=suppression.path,
                range=Range(Position(suppression.line, 1), Position(suppression.line, 1)),
                message=f"Suppression did not suppress any current finding ({rule}).",
                evidence={
                    "suppression": suppression.raw,
                    "line_text": suppression.line_text,
                    "scope": "file" if suppression.file_wide else "line",
                },
                actions=[
                    _action(
                        "remove-suppression",
                        True,
                        "Remove the stale suppression after confirming it is not needed.",
                    )
                ],
            )
        )
    return active, stale


def _applies(suppression: Suppression, issue: Issue) -> bool:
    if suppression.path != issue.path:
        return False
    if suppression.rule is None and "expected-unused" in suppression.raw:
        if issue.rule not in EXPECTED_UNUSED_RULES:
            return False
    elif suppression.rule in ALIASES and issue.rule not in ALIASES[suppression.rule]:
        return False
    elif suppression.rule and suppression.rule not in ALIASES and suppression.rule != issue.rule:
        return False
    return suppression.file_wide or suppression.line == issue.range.start.line


def _action(action_type: str, safe: bool, description: str):
    from .models import Action

    return Action(action_type, safe, description)
