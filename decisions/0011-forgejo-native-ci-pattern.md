# 0011 — Adopt Forgejo-native CI pattern (from parallel Codex thread's stash)

**Date:** 2026-05-05
**Status:** accepted
**Supersedes (partially):** [0003](0003-forgejo-runner-ubuntu-latest.md) — workflow shape is upgraded; runner-image fix from 0003 stays accepted
**Authors:** operator (`pdurlej`) — decision-maker; Claude Opus 4.7 — recording

## Context

ADR 0003 fixed the immediate Phase A blocker (`container: image: python:3.12` lacked Node.js, breaking `actions/checkout@v4`). The fix used `runs-on: ubuntu-latest` + `actions/checkout@v4` + `actions/setup-python@v5` — same shape as `.github/workflows/ci.yml`. That was sufficient to unblock A3 and produced live-verified green CI run on rs2000 (Forgejo Actions run id 39).

In parallel during Phase A, a **separate Codex thread** (operator was working on platform on a different session simultaneously) developed a **better** pattern on the same `feat/phase-a-ship-blockers` worktree. The work was uncommitted and ended up in `stash@{0}` after orchestrator stashed it for clean Phase A merge:

> `stash@{0}: CI refactor work from parallel Codex thread (2026-05-04)`

The stash contains:
- `.forgejo/workflows/ci.yml` rewrite with **Forgejo-native action URLs** (`https://data.forgejo.org/actions/checkout@v4` instead of `actions/checkout@v4`) — avoids GitHub rate-limit on Forgejo runner
- `runs-on: ubuntu-22.04` (explicit pin, not `ubuntu-latest`)
- `persist-credentials: false` on checkout (security default)
- `enable-email-notifications: false` on workflow header (ergonomics)
- New `scripts/ci/run_python_ci.py` (~131 lines) — Python runner script that owns the CI logic (install / compile / test / self-audit / CLI smoke / MCP / build) and produces structured `ci-artifacts/ci-report.json` + `ci-feedback.md`. Workflow YAML becomes a thin wrapper invoking the script.
- `examples/ci/forgejo-actions.yml` updated with same Forgejo-native shape (template for users matches what platform actually uses)
- `examples/ci/README.md` updated with new instructions

ADR 0003 noted this stash as "not needed for basic CI to work — the simple A3 fix was sufficient" and treated it as optional Phase B/C refinement.

## Operator review 2026-05-05

When walked through this trade-off during Phase A retrospective voice review, operator decided:

> "Skoro Codex sam wpadł nie planując, no to ja uważam, że powinniśmy to używać i włączyć. (...) Sposób tworzenia kodów platform powinien być uniwersalnym źródłem wszystkich mikroprojektów."

Translation: "Since Codex independently arrived at this pattern without prior planning, I think we should use it and enable it. (...) The way platform builds code should be the universal source for all microprojects."

Two reasons to adopt:
1. **Platform parity.** `pdurlej/platform/.forgejo/workflows/python-ci.yml` already uses this exact pattern — Forgejo-native URLs, `ubuntu-22.04`, `persist-credentials: false`, `enable-email-notifications: false`. Pyfallow workflow trailing platform's pattern is drift; pyfallow leading or matching is consistency.
2. **Convergent design.** Two independent agents (the parallel Codex thread + this orchestrator's later platform PR #71) arrived at the same pattern when given the same problem (Forgejo runner CI) without coordination. That's a strong signal the pattern is right.

## Decision

Stash content gets unstashed and merged into `pdurlej/pyfallow/main` via a new branch `feat/forgejo-native-ci-from-stash` and PR (forthcoming, sister to this ADR's PR).

Components:

1. `.forgejo/workflows/ci.yml` rewritten to use:
   - `https://data.forgejo.org/actions/checkout@v4` and `https://data.forgejo.org/actions/setup-python@v5`
   - `runs-on: ubuntu-22.04`
   - `persist-credentials: false` on checkout
   - `enable-email-notifications: false` on workflow header
   - Workflow body delegates to `scripts/ci/run_python_ci.py`

2. `scripts/ci/run_python_ci.py` added (Python runner script). 131 lines. Owns the CI orchestration; produces `ci-artifacts/ci-report.json` + `ci-feedback.md`.

3. `examples/ci/forgejo-actions.yml` updated to match (template for downstream users mirrors what pyfallow actually uses).

4. `examples/ci/README.md` updated with instructions for the new shape.

Authorship of the resulting commit credits the parallel Codex thread via `Co-Authored-By: codex <codex@noreply.git.pdurlej.com>` trailer; primary author is the orchestrator (`claude`) since this orchestrator is performing the unstashing-and-cleanup. Authentic attribution.

ADR 0003's runner-image-fix (drop `container:` directive, use `ubuntu-latest`) is **kept** — that was the immediate blocker fix and remains correct conceptually. ADR 0011 supersedes the *workflow-shape* part of 0003 with the more refined pattern. ADR 0003 stays in history with status `partially superseded by 0011`.

## Consequences

**Positive:**
- Platform ↔ pyfallow CI shape parity. Future updates touch both repos with identical patterns.
- Forgejo-native URLs avoid GitHub rate-limit on Forgejo runners (intermittent issue in heavier CI usage).
- Python runner script (`scripts/ci/run_python_ci.py`) makes CI logic testable — orchestrator can run the same script locally as a pre-PR check, no need to push to verify CI shape.
- `ci-artifacts/ci-report.json` schema is consumable by next-agent-in-chain (Codex iterating after CI feedback).

**Negative:**
- Adds a Python script (`scripts/ci/run_python_ci.py`) to repo. New file = new maintenance surface. Acceptable given the cleanup it produces in workflow YAML.
- Forgejo-native URLs (`data.forgejo.org`) tie the workflow to Forgejo infrastructure availability. If Forgejo's mirror is down, CI breaks. Mitigation: fallback to `actions/...` URLs in case of Forgejo mirror failure (separate ticket if needed; not solving for it now).

**Neutral:**
- This pattern is explicitly **not** a Show HN polish item — it's internal CI hygiene. Won't show in README or marketing.

## References

- ADR 0003 — predecessor that fixed the immediate runner blocker (partially superseded by this ADR)
- `stash@{0}` (now applied) — original parallel-thread work, attribution preserved via Co-Authored-By
- `pdurlej/platform/.forgejo/workflows/python-ci.yml` — pattern source / parity target
- `pdurlej/platform` PR #71 — first instance of orchestrator using the same pattern in another repo (convergent independent design)
- Forgejo Actions documentation for `data.forgejo.org` action mirrors
- Forgejo issue (forthcoming on `feat/forgejo-native-ci-from-stash` branch's PR) — implementation ticket
