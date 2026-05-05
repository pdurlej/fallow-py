# 0001 — Classification namespace = underscore

**Date:** 2026-05-04
**Status:** superseded by [0009](0009-three-bucket-classification.md) (2026-05-05)
**Phase:** A1
**Authors:** Claude Opus 4.7 (orchestrator), Codex (executor)

> **Supersession note (2026-05-05):** ADR 0001 unified the namespace correctly (silent bug resolved), but the four-bucket model itself was unexamined. Operator review 2026-05-05 surfaced that `manual_only` violates pyfallow's mission (asks non-technical operator to flip a coin) and `review_needed` is mis-named (programmer-language, not product-language). ADR 0009 supersedes with three-bucket model: `auto_safe` / `decision_needed` / `blocking` with mandatory product-language `trade_offs` explainability. The namespace-unification work in this ADR (Phase A commit `771c628`) stays — no code is reverted; ADR 0009 specifies the next migration in Phase B (issue #27).

## Context

Pre-Phase-A, MCP package `mcp/src/pyfallow_mcp/` carried two parallel namespaces for finding classification:

- **Underscore** (dominant, used in 6+ locations): `auto_safe`, `review_needed`, `blocking`, `manual_only` — defined in `pyfallow.classify.CLASSIFICATION_GROUPS`, used by `Finding.classification`, `Remediation.classification`, `runtime.findings()`, `tools.analyze_diff_impl()`, all `AnalysisResult` field names.
- **Hyphen** (in 2 locations): `safe-auto`, `review-needed`, `manual-only` (no `blocking`!) — used in `mcp/src/pyfallow_mcp/schemas.py::Classification.decision` Literal and four hardcoded strings in `mcp/src/pyfallow_mcp/safety.py:safe_classification`.

This was a silent bug. Agents calling `analyze_diff` (returns `Finding` with `auto_safe`) **and** `safe_to_remove` (returns `Classification` with `safe-auto`) on the same finding got different vocabulary. No schema validation caught it because `FlexibleModel(extra="allow")` masked drift. Audit GLM-5.1 2026-05-03 surfaced as F-11 critical.

Additionally, `mcp/src/pyfallow_mcp/safety.py:34` contained:

```python
return classify_finding(issue).decision == "auto_safe"
```

`classify_finding` returns underscore, but `safe_classification` was setting `decision="safe-auto"` on the Pydantic model. The comparison was a tautology of False — `safe_to_remove` literally never returned `auto_safe`, regardless of finding properties.

## Decision

All MCP classification labels mirror `pyfallow.classify.CLASSIFICATION_GROUPS` underscore namespace: `auto_safe`, `review_needed`, `blocking`, `manual_only`. Single source of truth in core; every other surface (CLI agent-fix-plan, MCP `analyze_diff`, MCP `safe_to_remove`, MCP `Classification.decision`, `Finding.classification`, `Remediation.classification`) renders that source — never duplicates.

`Classification.decision` Literal is extended to include `blocking` (mirroring core) even though `safe_classification` does not currently emit it for `unused-symbol`/`unused-module` rules. Defensive contract: if a future code path uses `Classification` for blocking-class findings, the type system already accepts it.

A drift-detection test suite at `mcp/tests/test_classification_namespace.py` fails fast (CI catches before merge) if any MCP `Literal[...]` diverges from core `CLASSIFICATION_GROUPS`. Includes a canary: `safe_classification` must return `decision="auto_safe"` for a high-confidence clean dead-code finding. Reverting any namespace change → red test.

## Consequences

**Positive:**
- `safe_to_remove` now correctly classifies high-confidence dead code as `auto_safe`. Previously it always returned `manual_only` (silent failure of intended behavior).
- Cross-tool agent code can switch on a single classification namespace.
- Phase B ticket B5 (FlexibleModel hardening) becomes effective: with `extra="forbid"` on contract models + the namespace unified, any future drift gets caught by Pydantic validation, not just the bespoke drift test.

**Negative / breaking:**
- Wire format change. MCP `safe_to_remove` `decision` field now returns underscore values. Pre-`0.3.0a2` pyfallow-mcp was alpha + not on PyPI, so external client impact is local-dev only. CHANGELOG entry documents.
- The hyphen namespace is deprecated entirely. No backwards-compat shim.

**Neutral:**
- Choice of underscore vs hyphen was determined by minimum-diff: 6+ locations were already underscore, 2 were hyphen. Inverting would have been ~3x larger change.

## References

- Implementation: PR #1 (GitHub) / PR #2 (Forgejo) — commit `771c628`, branch `feat/phase-a-ship-blockers`
- Audit: `.codex/audits/glm-engineering-audit-2026-05-03.md` finding F-11 (CRITICAL)
- Drift test: `mcp/tests/test_classification_namespace.py`
- WORKFLOW rule violated by the bug: #11 (single source of truth across transports)
- Live verification on installed package from TestPyPI 0.3.0a2: classification namespace held end-to-end on fresh-venv smoke
