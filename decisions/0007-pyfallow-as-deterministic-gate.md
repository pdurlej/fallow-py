# 0007 — Pyfallow as deterministic code gate (counterpart to platform.exe)

**Date:** 2026-05-04
**Status:** accepted
**Authors:** Claude Opus 4.7 — articulating; operator (`pdurlej`) — direction
**Related:** ADR 0006 (dogfood pivot), `pdurlej/platform/PLATFORM_CONSTITUTION.md` (counterpart identity)

## Context

Pyfallow's identity has been **emerging implicitly** — a Python static analyzer for AI agents to call before commit. Phase A landed core fixes, but the question of "what is pyfallow's role in operator's broader ecosystem" was answered only fragmentarily across `.codex/VISION.md`, README marketing copy, and chat-log discussions. Without explicit articulation:

1. New agents (Codex, GLM, Haiku) joining the project drift on what counts as "in scope" for pyfallow rules
2. Operator can't reference a single canonical document when integrating pyfallow into other repos
3. Show HN positioning is unclear (yet another linter? agent-native? deterministic governance?)

`pdurlej/platform` provides a clean precedent: `PLATFORM_CONSTITUTION.md` declares `platform.exe` as **deterministic operator** for infrastructure manifests. Pure function, no memory between invocations, audit-logged, no opinions. Counterpart to Iskra (the operator's relational, memory-rich AI partner). This split — relational AI for navigation, deterministic operator for execution — is the operator's working architecture.

Pyfallow has the same shape, but for **code** instead of **infra manifests**.

## Decision

Pyfallow's role is articulated in `docs/philosophy.md` (committed in `docs/dogfood-and-philosophy` PR #3 by `claude` 2026-05-04) as:

> A non-technical operator orchestrating AI agents on production code needs deterministic, replayable, opinion-free gates between intent (a prompt, a planned commit) and reality (what actually lands on `main`). Without those gates, every commit becomes "I trust this LLM read the codebase right." That's slop-generation at scale.
>
> Pyfallow is one of those gates. It is not a creative collaborator. It is not a reviewer with taste. It is a pure function: `(repo state, config) → findings`. Replay with the same inputs → identical findings. No memory between invocations. No opinions about the code's purpose. No suggestions outside the documented rule set.
>
> That posture is the feature, not a limitation.

Pyfallow's position in operator's ecosystem (mirroring `PLATFORM_CONSTITUTION.md`'s position):

| Actor | Role | Domain |
|---|---|---|
| **Iskra** | Relational, memory-rich, reflects on operator's decisions | Conversation, reflection, suggestion |
| **`platform.exe`** | Deterministic, stateless, audit-logged | Infrastructure manifests ↔ runtime on RS 2000 + VPS 1000 |
| **Pyfallow** | Deterministic, stateless, audit-logged | Code structural integrity ↔ committed source |
| **Codex** | Producer; executes per master prompts | All edits to code, manifests, prompts |
| **3+3 canary ensemble** | Six diverse review voices | PRs touching governance paths |
| **Operator (`pdurlej`)** | Final approver | Merges, strategic decisions |

Pyfallow makes the same kind of promise `platform.exe` makes, just at a different layer:

- `platform.exe`: "what's in the manifest is what's running and nothing more"
- pyfallow: "what the agent claims it edited is what's structurally consistent in the repository graph"

## Promises pyfallow makes (consequence of identity)

Codified in `docs/philosophy.md` § "What pyfallow promises":

1. **Determinism.** Same repo state + same config → same fingerprints, same classification, same exit codes.
2. **Single source of truth across transports.** CLI, MCP, all renders from one classifier in `src/pyfallow/classify.py` (per ADR 0001).
3. **Conservative classification.** When in doubt → `review_needed` or `manual_only`. `auto_safe` reserved for genuinely safe-for-agent-action findings.
4. **Stable fingerprints.** Per ADR pending in Phase B (B8 ticket #11) — rule + symbol + canonical evidence, not traversal artifacts.
5. **Drift detection between transports.** Per ADR 0001 — `mcp/tests/test_classification_namespace.py` fails fast on Pydantic Literal divergence.
6. **Hostile-input safety.** Per ADR 0002 (baseline), Phase B issues #6 (symlink), #7 (sandbox).

## What pyfallow refuses to be (also identity)

- No opinions about whether code is "good" — only structural consistency
- No memory between invocations — pure function
- No opinion-based blocking — cyclomatic complexity etc. are `review_needed`, never `blocking`
- Doesn't require an LLM to interpret output — structured, typed, deterministic

## Consequences

**Positive:**
- New agents joining (and old agents resuming after compaction) have a single canonical document to ground their behavior on `pyfallow`. No more drift across `VISION.md`, README, chat logs.
- Operator's pitch for Show HN (when it happens) is clear: "deterministic gate that makes budget AI models ship structurally clean code; counterpart to my deterministic infra operator." Stronger than "yet another Python linter."
- Phase B / C ticket prioritization can refer back to "does this serve pyfallow's promises in `docs/philosophy.md`" as a sanity check.

**Negative:**
- Identity articulated this strongly may close off product directions later (e.g., adding opinion-based reviewer features would require ADR superseding 0007). Tradeoff accepted: Identity discipline > product flexibility, for a tool whose value proposition is "you can trust this layer."

**Neutral:**
- The articulation is **descriptive of how pyfallow already works**, plus normative for keeping it that way. Phase A behavior matches; Phase B / C tickets reviewed against the philosophy show no contradictions.

## References

- `docs/philosophy.md` — full text of pyfallow's role (committed in PR #3 by `claude`)
- `docs/dogfood.md` — operational counterpart (how to integrate pyfallow into a project)
- `pdurlej/platform/PLATFORM_CONSTITUTION.md` — `platform.exe` identity that this ADR mirrors for code
- ADR 0001 (single source of truth) — Promise #2 mechanically enforced
- ADR 0002 (baseline validation) — Promise #6 mechanically enforced
