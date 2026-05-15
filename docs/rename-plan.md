# Rename plan: pyfallow → fallow-py

**Status:** in-progress
**Owner:** operator (decision-maker) + Claude Opus 4.7 (executor)
**Decision record:** [ADR 0012](../decisions/0012-umbrella-branding-fallow.md)
**Started:** 2026-05-13
**Target completion:** before fallow-ts MVP ships (so the TS sibling can fork from a stable umbrella)

This document is the **rolling status** of the four-PR migration described in ADR 0012. Update each section as PRs land.

---

## Research findings (input that triggered this rename)

Research agent surveyed the TS/JS analyzer ecosystem 2025-2026. One-paragraph summary:

> Nothing in the TS/JS ecosystem matches pyfallow's identity end-to-end. The detection layer is well-covered by `knip` (unused symbols / dead exports / unused deps), `dependency-cruiser` (module graph + architecture boundaries), `tsc --noEmit --strict` (type integrity + broken imports), and `@arethetypeswrong/cli` (package-type publishing integrity). The missing layer is pyfallow's contract: three-bucket classification (`auto_safe` / `decision_needed` / `blocking`) with rationale, stable per-finding fingerprints with suppression survival, single source of truth across CLI + MCP. Knip's maintainer position is explicitly against per-finding suppression — incompatible with pyfallow's fingerprint model. Verdict: build a thin TypeScript orchestrator that subprocesses existing detection tools and owns the agent-facing contract. Estimated delta is small (a few thousand LOC), not a full new analyzer.

The full report (with comparison table and references) is in this conversation's thread; relevant excerpts to be preserved in the fallow-ts repo's own `docs/research-2026-05-13.md` when it ships.

---

## PR sequence

### PR #1 — ADR 0012 + this plan doc (docs only)

**Branch:** `rename/adr-umbrella-branding`
**Risk:** zero
**Status:** merged (#45)

Scope:
- New `decisions/0012-umbrella-branding-fallow.md`
- New `docs/rename-plan.md` (this file)
- `decisions/README.md` index updated

No source code touched. No CI / packaging / config changes. Pure documentation of the decision and the plan.

### PR #2 — Python package rename + import shim

**Branch:** `rename/package-fallow-py`
**Risk:** medium (largest mechanical diff)
**Status:** merged (#46)

Scope:
- `src/pyfallow/` → `src/fallow_py/` (full directory rename, preserving git history via `git mv`)
- All internal imports updated: `from pyfallow.X` → `from fallow_py.X`
- `src/pyfallow/__init__.py` left in place as a shim:
  ```python
  import warnings
  from fallow_py import *  # noqa: F401, F403
  warnings.warn(
      "`pyfallow` package name is deprecated; import from `fallow_py` instead. "
      "The shim will be removed in 0.4.0.",
      DeprecationWarning,
      stacklevel=2,
  )
  ```
- MCP package `mcp/src/pyfallow_mcp/` → `mcp/src/fallow_py_mcp/` (same pattern + shim)
- Tests pass (`python3 -m pytest -q`) on the renamed structure
- `pyfallow analyze` self-check still passes (no structural regressions)

Out of scope:
- pyproject.toml `[project]` table changes (handled in PR #3)
- CLI entry point name (handled in PR #3)
- Documentation rewrites (handled in PR #3)

### PR #3 — CLI command, config, packaging, docs

**Branch:** `rename/cli-config-docs`
**Risk:** low
**Status:** merged (#47)

Scope:
- `pyproject.toml`:
  - `name = "pyfallow"` → `name = "fallow-py"`
  - `[project.scripts]` adds `fallow-py = "fallow_py.cli:main"`; keeps `pyfallow` as an alias entry point that emits a deprecation banner before dispatching
  - `[tool.pyfallow]` → `[tool.fallow_py]` (table key only, semantic config schema unchanged)
- MCP `mcp/pyproject.toml`:
  - `name = "pyfallow-mcp"` → `name = "fallow-py-mcp"`
  - `[project.scripts]` adds `fallow-py-mcp`; keeps `pyfallow-mcp` alias
- Config loader: read `.fallow-py.toml` as canonical, fall back to `.pyfallow.toml` with `DeprecationWarning`
- Sample config file shipped as `.fallow-py.toml` (this repo's own working config)
- Documentation rewrites:
  - `README.md`
  - `AGENTS.md`
  - `docs/philosophy.md`
  - `docs/dogfood.md`
  - `docs/dogfood-log-template.md`
  - `docs/performance.md` (if it mentions the brand)
  - `CHANGELOG.md` — add 0.3.0a3 entry noting the rename
  - `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` if they reference the brand
- Examples: `examples/ci/forgejo-actions.yml` + `examples/ci/README.md` show `pip install fallow-py` (or pinned `fallow-py==0.3.0a3`)
- ADR-immutability respected: past ADRs (0001-0011) keep "pyfallow" references; only ADR 0012 and this plan doc reference "fallow-py" as canonical

Out of scope:
- Repo rename (PR #4)
- Removing the `pyfallow` shim / alias / config fallback (0.4.x release)

### PR #4 — Admin repo rename

**Branch:** N/A (admin operation)
**Risk:** low (Forgejo preserves PRs / issues / forwarding redirects)
**Status:** admin rename completed; URL cleanup in progress

Scope:
- Operator (or claude with admin PAT) renames the repo on Forgejo: `pdurlej/pyfallow` → `pdurlej/fallow-py`
- GitHub mirror: same admin rename on github.com
- Local checkouts: `git remote set-url origin https://git.pdurlej.com/pdurlej/fallow-py.git` (Forgejo's HTTP redirect will keep old URLs working for a while; explicit update prevents drift)
- Update package metadata and docs links that point at the old URL.

After PR #4 merges, the rename is observably complete.

---

## Out-of-scope (this rename does NOT touch)

- Test-name strings inside test bodies that reference "pyfallow" as a runtime artifact name — those test what the tool outputs at runtime, and would be updated alongside PR #3's CLI rename.
- Branch names in past ADRs / PR titles. Historical.
- Past dogfood log entries (if any reference "pyfallow"). Historical.
- The fallow-ts sibling project. ADR 0012 mentions its existence; its repo, package name, MCP server, etc. are decided inside the forked conversation that drives fallow-ts development.

---

## Update log

- **2026-05-13** — PR #1 opened (this doc + ADR 0012). Status: in review.
- **2026-05-15** — PR #1 merged as #45; PR #2 started on `rename/package-fallow-py`.
- **2026-05-15** — PR #2 merged as #46; PR #3 started on `rename/cli-config-docs`.
- **2026-05-15** — PR #3 merged as #47; Forgejo and GitHub repos renamed to `fallow-py`; URL cleanup started on `rename/repo-url-cleanup`.
