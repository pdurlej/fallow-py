# 0007 — Pyfallow as bassist (deterministic harness, not agent)

**Date:** 2026-05-04 (metaphor refined + harness-vs-agent distinction added 2026-05-05)
**Status:** accepted
**Authors:** Claude Opus 4.7 — articulating; operator — direction + metaphor
**Related:** ADR 0006 (dogfood pivot, anti-AI-slop), ADR 0010 (mandatory non-author reviewer)

> **Edit note 2026-05-05:** Original draft used "deterministic gate" as primary framing. Operator review surfaced a better metaphor — **bassist** (musical) — and an important categorical distinction: **AI agent vs harness**. This edit promotes the bassist metaphor to primary; "deterministic gate" stays as the technical description. Decision intent unchanged.

## Context

Pyfallow's identity has been **emerging implicitly** — a Python static analyzer for AI agents to call before commit. Phase A landed core fixes, but the question of "what is pyfallow's role in operator's broader ecosystem" was answered only fragmentarily across `.codex/VISION.md`, README marketing copy, and chat-log discussions. Without explicit articulation:

1. New agents (Codex, GLM, Haiku) joining the project drift on what counts as "in scope" for pyfallow rules
2. Operator can't reference a single canonical document when integrating pyfallow into other repos
3. Show HN positioning is unclear (yet another linter? agent-native? deterministic governance?)

The operator's broader workflow provides a clean precedent: deterministic gates check declared intent against reality. Pure function, no memory between invocations, audit-logged, no opinions. This split — relational AI for navigation, deterministic tools for execution — is the operator's working architecture.

Pyfallow has the same shape, but for **code** instead of **infra manifests**.

## Decision

Pyfallow's role is articulated in `docs/philosophy.md` (committed in `docs/dogfood-and-philosophy` PR #3 by `claude` 2026-05-04) as:

> A non-technical operator orchestrating AI agents on production code needs deterministic, replayable, opinion-free gates between intent (a prompt, a planned commit) and reality (what actually lands on `main`). Without those gates, every commit becomes "I trust this LLM read the codebase right." That's slop-generation at scale.
>
> Pyfallow is one of those gates. It is not a creative collaborator. It is not a reviewer with taste. It is a pure function: `(repo state, config) → findings`. Replay with the same inputs → identical findings. No memory between invocations. No opinions about the code's purpose. No suggestions outside the documented rule set.
>
> That posture is the feature, not a limitation.

Pyfallow's position in the operator's ecosystem:

| Actor | Role | Domain |
|---|---|---|
| **Relational assistant** | Vocalist — memory-rich, reflects on operator decisions | Conversation, reflection, suggestion |
| **Infrastructure gate** | Deterministic, stateless, audit-logged — **harness** | Declared infrastructure intent ↔ runtime reality |
| **Pyfallow** | Bassist — deterministic, stateless, audit-logged — **harness** | Code structural integrity ↔ committed source |
| **Codex** | Producer / drummer — executes per master prompts (rhythm + execution) | All edits to code, manifests, prompts |
| **Claude / Opus** | Lead guitarist — orchestrates, articulates, holds strategic context | PM-role, review, briefs, coordination |
| **3+3 canary ensemble** | Six review voices (musical critics) | PRs touching governance paths |
| **Operator** | Bandleader — final approver | Merges, strategic decisions, breakglass |

## Bassist metaphor (operator's framing, 2026-05-05)

> "Pyfallow ma być basistą, jak w zespole muzycznym. Pyfallow ma być z tyłu zespołu agentów. Robić robotę i sprawdzać, żebyście mogli shine. Podobnie jak Forgejo Actions."

Translation: "Pyfallow should be the bassist, like in a music band. Pyfallow stands behind the agent band. Doing the work and checking, so you can shine. Like Forgejo Actions."

Bassist is in nearly every song. Holds the rhythm. **Doesn't try to be the lead vocal.** Without a bassist, the band sounds empty; with a bassist, vocalist and lead guitarist shine. The audience often doesn't notice the bassist — that's part of the role. The bassist is felt more than heard.

Pyfallow = bassist for the AI-agent band.

## AI agent vs harness (operator's distinction, 2026-05-05)

> "Jedna rzecz to AI agent. Druga rzecz to harness — MCP, tool-skill. Pyfallow ma być basistą."

Translation: "One thing is AI agent. Another thing is harness — MCP, tool-skill. Pyfallow should be the bassist."

Two categories of technical infrastructure in operator's ecosystem:

| Category | Examples | Job |
|---|---|---|
| **AI agent** | Codex, Claude / Opus, GLM, and peers | Reason, plan, decide, articulate, generate |
| **Harness** | Pyfallow, MCP servers, Forgejo Actions, pytest, ruff, mypy, infrastructure gates | Verify, gate, render, store, execute deterministically |

Harness ≠ agent. Harness is **stateless tooling** that agents (or operators) call. Agents have memory and judgment (taste, preference, opinion). Harness has **inputs and outputs** and **never an opinion**.

Pyfallow is a harness. Bassist. Disciplined background member.

Pyfallow makes the same kind of promise infrastructure gates make, just at a different layer:

- infrastructure gate: "declared state matches runtime state"
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
- Operator's pitch for Show HN (when it happens) is clear: "deterministic gate that makes budget AI models ship structurally clean code." Stronger than "yet another Python linter."
- Phase B / C ticket prioritization can refer back to "does this serve pyfallow's promises in `docs/philosophy.md`" as a sanity check.

**Negative:**
- Identity articulated this strongly may close off product directions later (e.g., adding opinion-based reviewer features would require ADR superseding 0007). Tradeoff accepted: Identity discipline > product flexibility, for a tool whose value proposition is "you can trust this layer."

**Neutral:**
- The articulation is **descriptive of how pyfallow already works**, plus normative for keeping it that way. Phase A behavior matches; Phase B / C tickets reviewed against the philosophy show no contradictions.

## References

- `docs/philosophy.md` — full text of pyfallow's role (committed in PR #3 by `claude`)
- `docs/dogfood.md` — operational counterpart (how to integrate pyfallow into a project)
- ADR 0001 (single source of truth) — Promise #2 mechanically enforced
- ADR 0002 (baseline validation) — Promise #6 mechanically enforced
