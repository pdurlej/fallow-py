# 0002 — Baseline JSON validation raises ConfigError

**Date:** 2026-05-04
**Status:** accepted
**Phase:** A2
**Authors:** Claude Opus 4.7 (orchestrator), Codex (executor)

## Context

`src/pyfallow/baseline.py::read_baseline()` previously parsed JSON and returned the raw dict without type validation:

```python
def read_baseline(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())
```

Malformed input — most commonly integer fingerprints from a manual edit, merge conflict, or tooling bug — caused a cryptic `TypeError` deep in `compare_with_baseline()` when `sorted()` was called on a mixed-type list. The user saw a stack trace with no indication that the baseline file was malformed.

Audit GLM-5.1 2026-05-03 finding F-17 elevated this from MEDIUM to HIGH because:
1. CI workflows depend on baseline comparison in `--baseline` invocations
2. The error type contract was unstable (TypeError vs ValueError vs random behavior)
3. The user's first signal was a traceback inside pyfallow's internals, not a "your file is malformed" message

## Decision

`read_baseline()` validates the loaded structure via a new `_validate_baseline_shape()` helper, raising `pyfallow.config.ConfigError` (the existing user-input error type) on any contract violation:

- Top level must be a JSON object
- `version` field must exist and be a string
- `fingerprints` field must exist and be a list (legacy format) **or** `issues` field must exist with a list of objects each having a string `fingerprint`
- All fingerprint values must be strings

Error messages include the file path and the specific field at fault. Up to 5 bad indices are listed when validation fails on a list (UX cap to keep errors readable on baselines with many violations).

`json.JSONDecodeError` is also wrapped in `ConfigError` for a consistent error type contract from this entry point.

CLI maps `ConfigError` to exit code 2 (already established convention in pyfallow CLI).

## Consequences

**Positive:**
- Repro from the audit (`{"version": "1.0", "fingerprints": [12345, 67890]}`) now produces a clear error message naming the malformed field at indices `[0, 1]`, exit code 2 — not a traceback.
- All other readers of `baseline` data downstream can assume well-formed input. Removes defensive checks scattered later in the pipeline.
- 5 new tests in `tests/test_baseline.py` provide regression coverage.

**Negative:**
- Consumers that previously caught `TypeError` from `compare_with_baseline()` to detect malformed input must switch to `ConfigError`. Internal tooling only — no external API contract change.
- Adds a small validation pass on every baseline load. Cost is O(n) over fingerprints; negligible at any realistic baseline size.

**Neutral:**
- Baselines with extra top-level fields (forward compat) are still accepted. Strictness is on required fields only.

## References

- Implementation: PR #2 (Forgejo) — commit `7307cd6`, branch `feat/phase-a-ship-blockers`
- Audit: `.codex/audits/glm-engineering-audit-2026-05-03.md` finding F-17 (HIGH; was F-08 MEDIUM in earlier session)
- Tests: `tests/test_baseline.py` — 5 cases (integer fingerprints, missing version, non-object top, invalid JSON, valid baseline accepted)
