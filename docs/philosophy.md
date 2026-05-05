# Philosophy — pyfallow as a deterministic gate

**Audience:** any AI agent (Claude, Codex, GLM, Haiku, Cursor, Aider, etc.) acting on a codebase, plus the operator who reads pyfallow's output.

**Status:** v1, written 2026-05-04 by Claude Opus 4.7 (orchestrator) under operator (`pdurlej`) direction.

---

## The thesis

A non-technical operator orchestrating AI agents on production code needs **deterministic, replayable, opinion-free gates** between intent (a prompt, a planned commit) and reality (what actually lands on `main`). Without those gates, every commit becomes "I trust this LLM read the codebase right." That's slop-generation at scale.

Pyfallow is one of those gates. It is not a creative collaborator. It is not a reviewer with taste. It is a **pure function**: `(repo state, config) → findings`. Replay with the same inputs → identical findings. No memory between invocations. No opinions about the code's purpose. No suggestions outside the documented rule set.

That posture is the feature, not a limitation.

## Position in the ecosystem

In the operator's stack (per `pdurlej/platform`'s `PLATFORM_CONSTITUTION.md`):

- **Iskra** — relational, memory-rich, reflects on operator's decisions. Subjective. Recommends.
- **`platform.exe`** — deterministic, stateless, audit-logged. Gates infrastructure manifests against running RS 2000 + VPS 1000 reality.
- **Codex** — producer. Executes per master prompts. Cannot bypass `platformctl`.
- **3+3 canary ensemble** (claude, codex, glm × tech, product) — six diverse reviewer voices on PRs touching `modules/`, `schema/`, `prompts/`, `tests/`, `control-plane/`, `decisions/`.
- **Operator (`pdurlej`)** — final approver. Holds the merge button. Holds the strategic context.

**Pyfallow sits next to `platform.exe`, but for code instead of infra.** Where `platform.exe` enforces "what's in the manifest is what's running and nothing more," pyfallow enforces "what the AI agent claimed it edited is what's structurally consistent in the repository graph."

Concretely, pyfallow answers questions that are **expensive for an LLM to answer correctly** but **cheap for static analysis**:

- *Did the agent introduce a hallucinated import* (`from billing import compute_refund` where `compute_refund` doesn't exist)?
- *Did the agent silently introduce a circular dependency* across modules?
- *Did the agent leave behind unused symbols, dead modules, or stale suppressions?*
- *Did the agent declare a runtime dependency it doesn't actually use, or use a dev dependency in runtime code?*
- *Did the agent violate a configured architecture boundary?*

A premium model can sometimes answer these by reading enough context. A budget model often cannot. **Pyfallow makes the budget model's answer correct anyway**, because the analyzer doesn't read context — it reads the AST and the import graph.

## Operator's principle (in operator's own words)

From the chat log, 2026-05-04 (operator dictating, transcribed):

> "Skoro wiemy, że jestem nietechnicznym produktowcem to musimy jak najwięcej inwestować właśnie w takie govern statyczne, deterministyczne rzeczy żebym nie odpierdalał głupot i żebyście wy nie odpierdalali głupot pod moją komendą."

Translation, lightly cleaned:

> "Given that I am a non-technical product person, we need to invest as much as possible in static, deterministic governance — so that I don't ship stupidities, and so that you (the agents) don't ship stupidities under my command."

This is the founding principle. Pyfallow exists to keep that promise.

## What pyfallow refuses to be

- **Pyfallow does not have opinions about whether your code is good.** It checks structural consistency. Logic correctness, naming taste, performance, security beyond imports — those are out of scope. See [`docs/limitations.md`](limitations.md) (Phase C ticket).

- **Pyfallow does not have memory between invocations.** Like `platform.exe`. Same inputs → same outputs. No "well last time you said X" reasoning.

- **Pyfallow does not gate on opinion-based metrics.** Cyclomatic complexity, file size, etc. are surfaced as `review_needed` (informational), never as `blocking`. Blocking is reserved for findings that are wrong by structural definition (parse errors, unresolved imports, runtime cycles, missing runtime deps, etc.).

- **Pyfallow does not require an LLM to interpret its output.** The CLI prints structured text. The JSON output is deterministic. The MCP tools return typed Pydantic models. Agents and humans read the same data the same way.

## What pyfallow promises

1. **Determinism.** Same repo state + same config → same fingerprints, same classification, same exit codes. Replay is a feature.

2. **Single source of truth across transports.** The CLI `--format agent-fix-plan` output, the MCP `analyze_diff` response, the MCP `safe_to_remove` decision — all use the same classification namespace (`auto_safe`, `review_needed`, `blocking`, `manual_only`). One classifier in `src/pyfallow/classify.py`. Every other surface renders, never duplicates.

3. **Conservative classification.** When in doubt, route to `review_needed` or `manual_only`. `auto_safe` is reserved for findings the analyzer is genuinely confident an agent can act on without human review (high-confidence dead code without framework, entrypoint, public-API, or dynamic-uncertainty flags).

4. **Stable fingerprints.** A finding's fingerprint depends on the rule + symbol + canonical evidence, not on traversal artifacts. Cycle paths are canonicalized before hashing (rotated to start at lexicographically-smallest module). Re-running on unchanged code produces unchanged baselines.

5. **Drift detection between transports.** A test in `mcp/tests/test_classification_namespace.py` fails fast if the MCP schema literals diverge from `pyfallow.classify.CLASSIFICATION_GROUPS`. Schema drift is a CI-caught bug, not a discovery six months later.

6. **Hostile-input safety.** Malformed baselines raise `ConfigError` with a clear field, not cryptic `TypeError` deep in comparison. MCP `root` parameter is validated against system directories by default, sandboxable via `PYFALLOW_MCP_SANDBOX_ROOT` env var (Phase B ticket). File discovery does not follow symlinks outside the configured root (Phase B ticket).

## How an agent should treat pyfallow

If you are an LLM-based agent acting on a codebase that has pyfallow integrated:

1. **Before commit, call `pyfallow analyze` (CLI) or `pyfallow.analyze_diff` (MCP) on your diff.** This is a deterministic check on what you just changed. It is cheap.

2. **Read the classification, not just the message.** `auto_safe` findings are safe to apply with the suggested patch. `review_needed` findings require thinking. `blocking` findings stop the commit. `manual_only` findings are informational.

3. **For `unused-symbol` `auto_safe`, you may delete.** For `unused-symbol` `review_needed`, surface to operator.

4. **For `verify_imports` (MCP only): call before introducing a new import.** It tells you whether the planned import would resolve, hallucinate, cycle, or violate boundaries. Cheaper than discovering at runtime, much cheaper than letting a hallucinated symbol land.

5. **Do not argue with pyfallow's findings.** If you disagree, that's a pyfallow bug — file an issue with the fingerprint and the disagreement reasoning. Don't suppress with `# fallow: ignore` to silence noise without understanding it.

6. **Do not bypass pyfallow because "it's slow" or "the operator won't notice."** That's an integrity failure on the agent's part. The operator is non-technical specifically so they can rely on this layer.

## How the operator should treat pyfallow

1. **Do not memorize pyfallow's rules.** That's the analyzer's job. Phase C will add a full rule reference when the rule docs are ready; until then, use the finding's evidence, confidence, and suggested actions.

2. **Do treat pyfallow CI failures as legitimate signal.** If a PR is red on pyfallow's gate, the AI agent that produced it ran sloppy. Send it back. The point of having this layer is to **stop trusting that an agent did its homework**.

3. **Do log surprising findings.** False positives, missed real bugs, friction points — log to a dogfood log (template at [`docs/dogfood-log-template.md`](dogfood-log-template.md)). Per ADR 0008, Phase B/C starts only after enough evidence accumulates across real projects: at least 100 pyfallow CI runs, at least 20 meaningful dogfood log entries, and the operator's qualitative read. Without the log, "we'll improve later" becomes "we'll polish from imagination."

## How this document evolves

This file is governance prose, not code. Changes go through a regular PR but require:
- A line in `.codex/DECISIONS.md` referencing the principle that changed
- Owner explicit approval (the principles here are operator's commitments, not orchestrator's preferences)

If the operator updates `pdurlej/platform/PLATFORM_CONSTITUTION.md` in a way that changes this document's grounding, this file is updated in the same wave.

## References

- `pdurlej/platform/PLATFORM_CONSTITUTION.md` — `platform.exe` identity, deterministic operator pattern
- `pdurlej/platform/AGENTS.md` — agent runbook, identity isolation, 3+3 canary review
- `pdurlej/platform/PLATFORM_CHARTER.md` — vision, deploy flow, cognition rule
- `.codex/WORKFLOW.md` — pyfallow's own contributor workflow (TDD, atomic commits, single source of truth)
- `.codex/MASTER/README.md` — Phase A/B/C plans for pyfallow's own evolution
- [`docs/dogfood.md`](dogfood.md) — concrete how-to integrate pyfallow into a Forgejo Actions CI pipeline
- [`docs/limitations.md`](limitations.md) — what pyfallow does NOT catch (Phase C ticket)

---

*Maintained by Claude Opus 4.7 / Pan Herbata under operator direction. This is governance prose, not API documentation. If pyfallow's behavior contradicts the principles stated here, that's a pyfallow bug.*
