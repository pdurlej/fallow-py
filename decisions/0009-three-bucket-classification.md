# 0009 — Three-bucket classification with mandatory product-language explanations

**Date:** 2026-05-05
**Status:** accepted
**Supersedes:** [0001](0001-classification-namespace-underscore.md) (which kept the four-bucket convention)
**Authors:** operator (`pdurlej`) — decision-maker; Claude Opus 4.7 — recording

## Context

ADR 0001 unified MCP classification namespace on the four-bucket convention from core: `auto_safe` / `review_needed` / `blocking` / `manual_only`. That ADR resolved the silent-bug drift between hyphen and underscore namespaces but left the four-bucket model itself unexamined.

During Phase A retrospective voice review (chat 2026-05-05 ~05:00), operator pushed back on `manual_only` and on the `review_needed` label name. Voice transcription (translated, lightly cleaned):

> "Manual_only is no good. Because if we have AI [helping] a human who can't deal with it the way I can — what does manual_only give me? It's like asking someone who is not competent to make the decision. You might as well flip a coin.
>
> `review_needed` strongly suggests programming-language nomenclature. `decision_needed` is more product-oriented. `auto_safe` is fine because it informs me that I can sleep peacefully. `decision_needed` doesn't say I should read something — it says I have to decide, and that's the point. `blocking` informs that something is not OK and I just can't move forward with it. The system doesn't have to know — it can explain what the problems are and tell what the trade-offs are, but the human has to take responsibility.
>
> This fits the philosophy of pyfallow that we are building."

The four-bucket model violates pyfallow's core mission as articulated in ADR 0007: deterministic governance for non-technical operator. `manual_only` is the analyzer admitting it doesn't know how to classify — and asking the operator to decide anyway. For a non-technical operator, that's no better than coin-flip.

`review_needed` is also misnamed: it suggests the operator should *read code* to make the decision — but operator is non-technical, code-reading isn't the route to a good decision for them. The operator needs **trade-offs explained in product language** so they can decide based on consequences, not based on code-comprehension.

## Decision

Three-bucket classification:

- **`auto_safe`** — analyzer is confident the AI agent can apply the suggested fix without operator review (e.g., delete unused symbol `_internal_helper` in `src/foo.py:42` that has no callers, no public-API export, no framework markers). Operator sleeps peacefully.

- **`decision_needed`** (renamed from `review_needed`) — analyzer found something that requires a human decision. Each `decision_needed` finding **must** include `trade_offs` describing options in product language ("declare missing dep — adds one line to pyproject.toml; remove import — requires editing 3 call sites; guard with try/except ImportError — only sensible if dep is optional"). Operator picks the option without reading code.

- **`blocking`** — analyzer found a deterministic structural problem the system refuses to commit (parse error, unresolved import, runtime cycle, missing-runtime-dependency declared as `error` severity). Each `blocking` finding **must** include `trade_offs` too — the system explains *why* it's blocked and what options exist, but does not auto-resolve. Operator chooses (fix code, explicitly waive with rationale, or escalate).

`manual_only` is **dropped entirely**. The bucket gets removed from `pyfallow.classify.CLASSIFICATION_GROUPS`, all schema Literals, drift tests, agent-fix-plan output, MCP `Classification.decision`, MCP grouped responses. Findings that previously routed to `manual_only` get re-classified:

- If they're real findings the operator should decide on → `decision_needed` with `trade_offs`
- If they're informational signals not requiring action → drop from analyzer entirely (they were noise)

## Mandatory explainability

Each `decision_needed` and `blocking` finding's serialized form (CLI text, JSON, MCP Pydantic) **must** include a `trade_offs` field (or equivalent — exact name to be confirmed during implementation in Phase B ticket #27 / B13).

The field is non-empty list of strings, each describing one option the operator can choose. Each option is product-language: "do X, costs Y, gives Z." No code references in the option text itself (links to file:line for context are fine, but the *decision* description is product-language).

Schema-enforced via Pydantic `Field(min_length=1)` on the contract models (`Finding.trade_offs`, `Remediation.trade_offs`, etc.). Drift test `mcp/tests/test_classification_namespace.py` extends to verify the field is populated for `decision_needed` and `blocking` findings.

## Consequences

**Positive:**
- Aligns classification model with operator's mission (deterministic governance for non-technical operator). No more coin-flip findings.
- Product-language `trade_offs` makes operator's decision low-cost — read 3 lines, pick one. Code-comprehension not required.
- `decision_needed` naming matches the actual semantic ("decision needed from someone competent"). `review_needed` was a programmer-default that drifted into the namespace by inertia.

**Negative:**
- **Wire format change.** All MCP clients see new namespace. Breaking from `0.3.0a2`. Documented in CHANGELOG, recorded in this ADR. Pre-stable, no external clients to migrate.
- **Migration burden.** Each rule that previously emitted `manual_only` needs explicit re-classification decision. Some rules might be dropped entirely if they were noise.
- **Implementation cost.** `trade_offs` field is new schema, requires Pydantic enforcement, drift test extension, all output formats updated, documentation updated. Real Phase B work.

**Neutral:**
- Issue #27 (B13: Drop `manual_only` from classification namespace + add mandatory explainability) tracks the implementation. Like all Phase B work, gated on dogfood evidence per ADR 0008.

## References

- ADR 0001 — predecessor with four-bucket model (now superseded)
- ADR 0007 — pyfallow's identity as deterministic gate; this ADR enforces that identity at the classification model
- Forgejo issue #27 — implementation ticket
- Operator's voice transcription, 2026-05-05 ~05:00 (recorded in this ADR's Context section)
