# 0003 — Forgejo runner = ubuntu-latest, not docker:python

**Date:** 2026-05-04
**Status:** partially superseded by [0011](0011-forgejo-native-ci-pattern.md) (2026-05-05)
**Phase:** A3
**Authors:** Claude Opus 4.7 (orchestrator), Codex (executor)

> **Supersession note (2026-05-05):** The runner-image fix (drop `container: python:3.12` directive, use `ubuntu-latest`) is correct and **stays accepted**. ADR 0011 supersedes the *workflow-shape* portion (now uses Forgejo-native action URLs `https://data.forgejo.org/...`, `ubuntu-22.04` explicit pin, `persist-credentials: false`, dedicated Python runner script `scripts/ci/run_python_ci.py`) per operator decision 2026-05-05 to adopt the parallel Codex thread's stash pattern. Reason: parity with the operator's existing Forgejo-native CI pattern, and convergent independent design (two agents arrived at same pattern without coordination = strong signal it's right).

## Context

`examples/ci/forgejo-actions.yml` (template shipped to pyfallow users for their own Forgejo CI) specified:

```yaml
jobs:
  pyfallow-cleanup:
    runs-on: docker
    container:
      image: python:3.12
```

Live PR test on 2026-05-03 (PR #1, since reverted) confirmed: every job failed at step 1 ("Check out") because `actions/checkout@v4` requires Node.js, and the `python:3.12` Docker image has no Node.js installed.

Additionally, after the live-validation PR was reverted, pyfallow's own Forgejo CI was empty — `.forgejo/workflows/ci.yml` was deleted in the revert. The Forgejo Actions runner was registered but had nothing to run. GitHub CI continued working but Forgejo (operator's primary remote) was effectively dark.

## Decision

Both files use the same shape, mirroring the working pattern from `.github/workflows/ci.yml`:

- `runs-on: ubuntu-latest` (Forgejo runner config maps this label to `catthehacker/ubuntu:act-latest`, which has both Node.js and Python preinstalled)
- No `container:` directive (was the blocker)
- Explicit `actions/setup-python@v5` step to select the desired Python version

Two files updated:
- `examples/ci/forgejo-actions.yml` — single-job template for users
- `.forgejo/workflows/ci.yml` (NEW) — pyfallow's own self-CI, full matrix `["3.11", "3.12", "3.13"]` mirroring GitHub workflow steps

Live verification was a release blocker for closure: PR #2 on Forgejo triggered run id 39 (trigger=pull_request) which completed with `status: success`. A3 is closed with **on-runner evidence**, not just yamllint + assertion test.

## Consequences

**Positive:**
- Forgejo CI works end-to-end on the configured runner. Live evidence captured as run id 39.
- GitHub ↔ Forgejo CI parity: same matrix, same steps, same runner-style. Future updates touch both files in lockstep.
- Forgejo PR template now matches what users on Forgejo Actions runners actually need (no GitHub-only assumptions).

**Negative:**
- Drops the `container:` directive even though it would let users specify exact Python images. Tradeoff: runner compatibility > image control. Users who need specific Python versions configure via `actions/setup-python@v5`.

**Neutral:**
- A parallel Codex thread (separate session) produced an alternative refactor for the workflow shape using Forgejo-native action URLs (`https://data.forgejo.org/actions/checkout@v4`), `ubuntu-22.04` (explicit pin), `persist-credentials: false`, plus a Python runner script `scripts/ci/run_python_ci.py`. That work landed in stash (`stash@{0}` on Phase A branch) but was **not needed** for basic CI to work — the simple A3 fix was sufficient. Stash is treated as optional Phase B/C refinement; will be picked up if intensifying CI usage hits GitHub rate limits or if other patterns from the refactor become necessary.

## References

- Implementation: PR #2 (Forgejo) — commit `33061c7`, branch `feat/phase-a-ship-blockers`
- Audit / discovery: live failure on PR #1 (since reverted), 2026-05-03
- Live verification: Forgejo Actions run id 39 (`status: success`, trigger `pull_request`)
- Stash from parallel thread: `stash@{0}: CI refactor work from parallel Codex thread (2026-05-04)` — may inform future Phase B/C ticket
