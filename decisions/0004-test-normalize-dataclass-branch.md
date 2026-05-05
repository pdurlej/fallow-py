# 0004 — Test `normalize()` handles FastMCP dataclass wrapping

**Date:** 2026-05-04
**Status:** accepted
**Phase:** A4
**Authors:** Claude Opus 4.7 (orchestrator), Codex (executor)

## Context

On Python 3.11.14 with `fastmcp` 3.2.4 and `pydantic` 2.13.3, FastMCP's `Client.call_tool()` returns the tool result wrapped in a **dynamically-generated dataclass** named `Root` with `__module__ == "types"`. On Python 3.13.1 the result comes back differently and the bug never surfaced locally.

`mcp/tests/test_mcp.py::normalize()` had branches for:
1. Pydantic BaseModel (uses `model_dump`)
2. fastmcp.* namespace classes (uses `vars()`)
3. dict / list / scalar passthroughs

It had no branch for dataclasses. On 3.11, `normalize()` fell through to `return value`, the test then tried `result["decision"]` on a `Root` instance and got `TypeError: 'Root' object is not subscriptable`.

**9 of 13 MCP tests failed on 3.11.** GitHub CI matrix includes 3.11. We had been pushing a broken matrix for an unknown duration. The audit GLM-5.1 2026-05-03 was run on Python 3.14 and didn't catch this — it surfaced during this orchestrator's verification of the Python 3.11 matrix as part of preparing the Phase A briefs.

## Decision

`normalize()` gains a `dataclasses.is_dataclass(value)` branch (with `not isinstance(value, type)` guard against class objects):

```python
def normalize(value):
    if hasattr(value, "model_dump"):
        return normalize(value.model_dump(mode="json"))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return normalize(dataclasses.asdict(value))
    if hasattr(value, "__dict__") and value.__class__.__module__.startswith("fastmcp."):
        return normalize(vars(value))
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value
```

Pure test plumbing change. Production code untouched. No Pydantic / FastMCP version pin.

## Consequences

**Positive:**
- 13/13 MCP tests pass on Python 3.11.14 (was 9 failed, 4 passed).
- 13/13 MCP tests still pass on Python 3.13.1 (no regression).
- CI matrix matches declared `requires-python = ">=3.11"`.
- Defensive: any future FastMCP version that returns yet another wrapper type will fail loudly on tests, not silently mask drift.

**Negative:**
- `normalize()` test helper grows by 2 lines. Acceptable.
- Couples test plumbing to FastMCP's runtime serialization details. If FastMCP changes wrapping shape again, helper needs another branch. Tradeoff: kept FastMCP version unpinned (security patches accessible) at the cost of helper maintenance.

**Neutral:**
- Branch order matters: `model_dump` first (Pydantic native), then `is_dataclass`. Pydantic v2 BaseModel is **not** a dataclass per `dataclasses.is_dataclass()`, so the branches are mutually exclusive in practice.

## Open question

Why does FastMCP return a dataclass with `__module__ == "types"` on 3.11 but not on 3.13? Possibly upstream behavior we should file an issue on. **Not a blocker for pyfallow** — the helper handles either shape — but worth tracking. Out of scope for A4; deferred to Phase B/C if relevant.

## References

- Implementation: PR #2 (Forgejo) — commit `527865e`, branch `feat/phase-a-ship-blockers`
- Discovery: this orchestrator's local verification setup, 2026-05-04 ~01:30 (using `uv venv --python 3.11` and reproducing 9-failed result)
- Reproducer venv: `/tmp/pyfallow-py311` (transient; recreate via `uv venv --python 3.11 /tmp/pyfallow-py311 && /tmp/pyfallow-py311/bin/python -m ensurepip && /tmp/pyfallow-py311/bin/python -m pip install -e ".[dev]" -e ./mcp`)
- Type signature of the wrapper observed: `class Root` with `__module__ == "types"`, `dataclasses.is_dataclass(value) == True`, `vars()` returns ordered field dict
