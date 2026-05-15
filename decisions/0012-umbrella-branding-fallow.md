# 0012 — Umbrella branding "fallow": pyfallow → fallow-py, new TS sibling → fallow-ts

**Date:** 2026-05-13
**Status:** accepted
**Authors:** operator — decision-maker; Claude Opus 4.7 — articulating
**Related:** ADR 0006 (dogfood pivot, anti-AI-slop), ADR 0007 (pyfallow as bassist / harness)

## Context

Operator observed that the share of TypeScript code across their working repositories is growing, and that pyfallow's deterministic-gate value is only available to Python projects. The natural follow-up question: build (or adopt) an analogous tool for TypeScript.

Research (handed to a research-only agent on 2026-05-13, summary captured in `docs/rename-plan.md` § "Research findings") concluded:

1. **No tool in the TS/JS ecosystem ships pyfallow's contract end-to-end.** The closest detection-layer candidates are `knip` (unused symbols / dead exports / unused deps), `dependency-cruiser` (module graph + architecture boundaries), `tsc --noEmit --strict` (type integrity + broken imports), and `@arethetypeswrong/cli` (package-type publishing integrity).
2. **The missing layer is the agent-facing contract** — three-bucket classification with rationale (`auto_safe` / `decision_needed` / `blocking`), stable per-finding fingerprints with suppression survival, single source of truth across CLI + MCP, deterministic hostile-input safety.
3. **The smallest path forward is to build a thin orchestrator in TypeScript** that subprocesses existing detection tools, normalizes their JSON to a single finding schema, applies pyfallow's classifier, and exposes the result identically over CLI and MCP.

Operator decided 2026-05-13 (voice review post-research): build this TS sibling. With the sibling on the roadmap, the question of branding presents itself for the first time. "pyfallow" reads as a Python-specific brand and would leave the future TS sibling brand-orphaned (`tsfallow`? `jsfallow`?), with no umbrella that ties the family together as one contract under multiple language implementations.

Operator's framing (voice, 2026-05-13):
> "trzeba zmienić wtedy nazwę na fallow-py i fallow-ts"

Translation: "we have to rename then to fallow-py and fallow-ts."

The "fallow" prefix already carries the project's metaphor (fallow land — let it rest, observe, don't force outcomes — anti-slop posture). It transfers cleanly to siblings.

## Decision

Adopt **"fallow"** as an umbrella brand for the project family. Concrete consequences:

| Asset | Before | After |
|---|---|---|
| Python implementation, repo | `pdurlej/pyfallow` | `pdurlej/fallow-py` |
| Python implementation, PyPI dist | `pyfallow` (0.3.0a2 published as historical) | `fallow-py` (canonical for 0.3.0a3+) |
| Python implementation, package | `src/pyfallow/` | `src/fallow_py/` |
| Python implementation, CLI command | `pyfallow` | `fallow-py` (with `pyfallow` alias on 0.3.x for compat) |
| Python implementation, MCP server | `pyfallow-mcp` | `fallow-py-mcp` |
| Python implementation, config file | `.pyfallow.toml` / `[tool.pyfallow]` | `.fallow-py.toml` / `[tool.fallow_py]` (dual-read on 0.3.x) |
| TypeScript sibling, repo (new) | — | `pdurlej/fallow-ts` (forked conversation starts here) |
| TypeScript sibling, npm dist (new) | — | `fallow-ts` or `@fallow/ts` (decided in fallow-ts repo) |

Future siblings (if/when warranted by evidence) follow the same pattern: `fallow-rs` for Rust, `fallow-go` for Go, etc. Each implementation owns its own repo, its own ADRs, its own dogfood window — bound together only by **the shared contract** (deterministic gate, three-bucket classification, stable fingerprints, single source of truth across CLI + MCP).

## Compatibility on 0.3.x cycle

Operator decided 2026-05-13 to bridge the rename with conservative backwards-compat:

1. **Python import shim.** `src/pyfallow/__init__.py` re-exports from `fallow_py` with a `DeprecationWarning`. Existing alpha users (`import pyfallow`) keep working through 0.3.x. Shim removed in 0.4.x.
2. **CLI command alias.** `pyfallow` stays as an entry point that dispatches to `fallow-py` (with deprecation banner) through 0.3.x. Removed in 0.4.x.
3. **Config dual-read.** `.fallow-py.toml` is canonical; `.pyfallow.toml` is read as fallback with a deprecation warning. Same lifecycle.

The 0.3.x → 0.4.x boundary is the cliff. Everything that lands in 0.3.x stays bilingual; everything from 0.4.x onwards is fallow-only.

## What does NOT change

- **Past ADRs (0001-0011)** keep their original "pyfallow" references. ADRs are immutable history per `decisions/README.md` convention. ADR 0007 (bassist metaphor) continues to apply — pyfallow / fallow-py is still the bassist, just under a new brand identity. ADR 0008 (evidence-bounded dogfood) continues to apply — the rename does not restart the evidence window.
- **Past PR / issue / review bodies** stay as written. Historical record.
- **Branch protection, mandatory non-author reviewer (ADR 0010)** unchanged — applies to renamed repo automatically.
- **Bassist metaphor (ADR 0007)** unchanged. The umbrella is descriptive of how the role transfers to siblings, not a change in role.

## Migration order

Rename is decomposed into four PRs to keep each reviewable. Rolling status in `docs/rename-plan.md`.

| PR | Scope | Risk |
|----|---|---|
| **#1 (this PR)** | ADR 0012 + `docs/rename-plan.md` rolling status doc | zero (docs only) |
| **#2** | `src/pyfallow/` → `src/fallow_py/`, all internal imports, shim left at old path; tests pass | medium (largest diff) |
| **#3** | CLI entry point `fallow-py` (+ `pyfallow` alias), config dual-read, all user-facing docs replaced | low |
| **#4** | Admin rename of repo on Forgejo + GitHub mirror; update remote URLs in local checkouts | low (Forgejo preserves PRs/issues/redirects) |

Each PR goes through ADR 0010 branch protection: ≥1 non-author AI reviewer + operator approval.

## Consequences

**Positive:**

- TS sibling has a coherent brand from day one without orphaning Python's identity. New agents joining either project can read "fallow" and know they're touching the same contract family.
- Future siblings (Rust, Go) inherit the convention. No ad-hoc renaming each time scope grows.
- The umbrella reinforces ADR 0007's posture: "fallow is a harness, not an agent" — the brand says one thing, multiple language implementations, one contract.
- Anti-slop discipline maintained: the rename was deferred until after research established that the TS sibling has a real reason to exist (knip + dependency-cruiser cover detection, agent-callable contract is the missing layer). Branding for a sibling that doesn't yet exist would have been speculative.

**Negative:**

- Rename touches ~95 files (mostly mechanical). Three PRs of meaningful diff to merge. Cost paid up-front so the TS sibling can fork from a stable umbrella.
- Existing alpha users (operator + agents, plus any one-off forks) must update imports / configs after 0.4.x. Mitigated by the 0.3.x compat shim period.
- One alpha already published on TestPyPI as `pyfallow 0.3.0a2`. That release stays as historical — no rename of published artifact. Next alpha (0.3.0a3+) ships under `fallow-py`. Users following the alpha line get a one-time migration.
- Documentation and external references (if any have started referring to "pyfallow" outside the repo) carry a forwarding burden. The dogfood window is small enough that this is bounded.

**Neutral:**

- Bassist metaphor and harness identity are brand-agnostic — they describe a role, not a name. The metaphor transfers cleanly.
- ADR-immutability convention means past decisions document "pyfallow" forever; that's correct history, not a regression.

## References

- `docs/rename-plan.md` — rolling status of the four-PR migration
- ADR 0006 — anti-AI-slop pivot (research-before-build discipline applied here)
- ADR 0007 — pyfallow as harness / bassist (role identity transfers to fallow-py + future siblings)
- ADR 0008 — evidence-bounded dogfood (unaffected — rename does not restart the window)
- ADR 0010 — mandatory non-author reviewer (applies to each rename PR)
