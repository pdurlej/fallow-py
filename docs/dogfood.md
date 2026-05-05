# Dogfood — pyfallow in your project's CI

**Audience:** operator (`pdurlej`) integrating pyfallow into other repositories he owns (`pdurlej/platform`, `pdurlej/hermes-agency`, `pdurlej/iskra-openclaw`, etc.) or any agent setting up such a CI pipeline.

**Status:** v1, written 2026-05-04. Tested against pyfallow `0.3.0a2` on TestPyPI.

**Why:** see [`docs/philosophy.md`](philosophy.md). Short version: a non-technical operator running multi-agent codebases needs a deterministic gate between agent commits and `main`.

---

## What you get

After integrating pyfallow into a Forgejo Actions workflow on a Python project:

- Every PR runs `pyfallow analyze` on the diff
- Findings are classified (`auto_safe` / `review_needed` / `blocking` / `manual_only`)
- A comment is posted on the PR with the agent-fix-plan output
- The job fails if there are `blocking` findings or warnings above threshold
- Artifacts (`pyfallow-report.json`, agent-readable feedback) are uploaded for the next agent in the chain to read

The agent that opened the PR (Codex, Claude, etc.) gets a deterministic answer to "is this commit structurally clean," independent of whether it had enough context to know.

## Prerequisites

- A Forgejo repo with Actions enabled (`has_actions: true` on the repo, runner registered)
- Python project with at least one `pyproject.toml` declaring entry points
- The repo's runner can pull container images and install Python packages from PyPI (or TestPyPI during pyfallow alpha)

## Minimal integration (3 steps)

### Step 1 — copy the workflow

Create `.forgejo/workflows/pyfallow.yml` in your project's repo. Start from the pyfallow-shipped template:

```bash
# In your project root (e.g., pdurlej/platform)
mkdir -p .forgejo/workflows
curl -sSL https://git.pdurlej.com/pdurlej/pyfallow/raw/branch/main/examples/ci/forgejo-actions.yml \
  -o .forgejo/workflows/pyfallow.yml
```

(Or copy by hand from `examples/ci/forgejo-actions.yml` in the pyfallow repo.)

### Step 2 — pin a pyfallow version

The shipped template installs the latest `pyfallow` from PyPI. During alpha (pre-`0.3.0` stable), pin to a specific TestPyPI version to avoid surprise breaks:

```yaml
# In .forgejo/workflows/pyfallow.yml, replace the install step with:

      - name: Install pyfallow (alpha pin)
        run: |
          python -m pip install --upgrade pip
          python -m pip install \
            --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            "pyfallow==0.3.0a2"
```

Once pyfallow lands on production PyPI as `0.3.0` stable, switch to `pip install pyfallow~=0.3.0` and remove the `--index-url` flags.

### Step 3 — configure pyfallow for your repo

Add a `.pyfallow.toml` (or `[tool.pyfallow]` table in `pyproject.toml`) declaring:

```toml
[tool.pyfallow]
roots = ["src"]                    # source code paths
entry = ["src/yourproject/main.py", "src/yourproject/cli.py"]
# entry = roots from which reachability is computed; everything not reached
# from any entry is candidate dead code

[tool.pyfallow.boundaries]
# (optional) architecture boundary rules
# Example: domain layer cannot import from infrastructure
"src/yourproject/domain/**" = { disallow = ["src/yourproject/infrastructure/**"] }

[tool.pyfallow.suppressions]
# (optional) global suppressions; prefer line-level `# fallow: ignore[<rule>]` instead
```

Then commit, push, open a PR. The runner pulls pyfallow, runs analyze on your diff, posts the comment, fails on blocking findings.

## Reading the CI comment as operator

The pyfallow comment on a PR will look like:

```
## pyfallow analysis

**Verdict:** DO NOT COMMIT (1 blocking)

### Blocking
- src/yourproject/payments.py:42 — missing-runtime-dependency
  Runtime import uses 'stripe', but it is not declared as a runtime dependency.
  Distribution: stripe

### Auto-safe
- (none)

### Review needed
- src/yourproject/utils.py:15 — unused-symbol `legacy_helper`
  Top-level function 'legacy_helper' is not referenced by analyzed modules.
  (medium confidence — could be framework-managed)
```

**Your decision tree as operator:**

| Verdict | What to do |
|---|---|
| All green ("No findings...") | Merge if review otherwise OK |
| Only `auto_safe` findings | Tell the agent: "apply the suggested patches in your next commit" |
| `review_needed` findings | Read them. Decide: legitimate FP (suppress) or real (fix) |
| `blocking` findings | **Send the PR back to the agent.** This is the whole point — pyfallow caught what the agent missed |

**Anti-pattern:** "the CI is red but the change looks fine, let me merge anyway." Don't. The agent that opened this PR is supposed to call pyfallow before pushing — if it didn't, that's an agent integrity failure that needs to surface, not be hidden.

## Reading the artifacts as a downstream agent

After the workflow runs, three artifacts are uploaded:

- `pyfallow-report.json` — full agent-fix-plan output (structured)
- `pyfallow-comment.md` — the rendered Markdown comment
- `pyfallow-exit-code.txt` — the analyzer's exit code

If your platform has a "next-agent picks up here" pattern (e.g., Codex reading PR feedback before iterating), point it at `pyfallow-report.json`. The structure is:

```json
{
  "schema_version": "1.0",
  "tool": "pyfallow",
  "version": "0.3.0a2",
  "summary": {
    "auto_safe_count": 0,
    "review_needed_count": 1,
    "blocking_count": 1,
    "manual_only_count": 0,
    "total": 2
  },
  "auto_safe": [],
  "review_needed": [
    {
      "fingerprint": "...",
      "rule": "unused-symbol",
      "id": "PY031",
      "file": "src/yourproject/utils.py",
      "line": 15,
      "symbol": "legacy_helper",
      ...
    }
  ],
  "blocking": [...],
  "manual_only": [],
  "limitations": [...]
}
```

An agent acting on this: iterate through `auto_safe` and apply patches; iterate through `blocking` and fix the root cause; surface `review_needed` to operator.

## Identity-isolation for agents (per platform AGENTS.md)

If an agent is committing to a repo that integrates pyfallow's CI workflow, it must commit with **its own identity**, not the operator's. Per `pdurlej/platform/AGENTS.md` § "Identity-isolation":

- Agent commits use `git config user.email "<actor>@noreply.git.pdurlej.com"` and `user.name "<actor>"`
- Agent pushes use the actor's PAT (from BW vault, item `git.pdurlej.com (<actor>)`, custom field `PAT`)
- Agent-created PRs use the actor's PAT in the `Authorization: token` header on the Forgejo API call — NOT the global Forgejo MCP (which is configured with operator's PAT)

This applies recursively: any new pyfallow-integrated repo inherits this convention. Pyfallow does not enforce it (out of scope), but if it's violated, audit logs will lie.

## Sister project: pyfallow-mcp

For agents using MCP transport (Claude Code, Cursor with MCP, etc.), `pyfallow-mcp` exposes the same analysis as MCP tools:

- `analyze_diff(root, since, min_confidence, max_findings)` — same as CLI agent-fix-plan but in-process
- `verify_imports(root, file, planned_imports)` — pre-edit hallucination check
- `safe_to_remove(root, fingerprints)` — agent asks "can I delete these N findings?" answer
- `agent_context(root, scope)` — full project overview for an agent starting cold
- `explain_finding(root, fingerprint)` — investigation hints + fix options for one finding

Install: `pip install pyfallow-mcp==0.1.0a2` (TestPyPI alpha, pinned alongside pyfallow `0.3.0a2`).

Wire into your agent's MCP config (Claude Code example):

```json
{
  "mcpServers": {
    "pyfallow": {
      "command": "pyfallow-mcp",
      "args": ["--root", "/path/to/your/project"]
    }
  }
}
```

For agents that use MCP, `verify_imports` is the highest-leverage tool: catch a hallucinated import **before** the edit lands, so you don't even need a second turn to fix it.

## Dogfood expectations (evidence-bounded window)

Operator's strategic decision (chat log 2026-05-04, refined in ADR 0008 on 2026-05-05): pyfallow does **not** push to Show HN until we have evidence from real-world dogfood. The window is evidence-bounded, not calendar-bounded:

- Pyfallow `0.3.0a2` integrated into `pdurlej/platform` first, then other Piotr's projects (`hermes-agency`, `iskra-openclaw`, etc.) as appetite allows
- Operator and agents log surprising findings, FPs, missed real bugs, friction in a dogfood log (template at [`docs/dogfood-log-template.md`](dogfood-log-template.md)) in the **pyfallow** repo
- Phase B/C starts only after the evidence threshold is met: at least 100 pyfallow CI runs across integrated repos, at least 20 meaningful dogfood log entries, and the operator's qualitative read. Plans in `.codex/MASTER/PHASE-B/` and `PHASE-C/` are not deleted — they are **subjected to evidence** before execution

This is anti-AI-slop posture: don't polish from imagination, polish from logs.

## When pyfallow is wrong

If you're confident pyfallow flagged something incorrectly:

1. Add `# fallow: ignore[<rule>]` on the line, with a comment explaining why
2. Open an issue at https://git.pdurlej.com/pdurlej/pyfallow/issues with:
   - Link to the suppressed line
   - Reasoning why it's a false positive
   - The rule code (e.g. `PY031`)
   - The fingerprint (from `pyfallow analyze --format json`)
3. The pyfallow Phase B/C planning will treat it as input for framework heuristic improvements

If you're confident pyfallow **missed** a real structural problem:

1. Same — open an issue, but with the reverse: "this committed code has structural issue X, pyfallow didn't flag it, expected behavior?"
2. Phase B already has tickets for known gaps (SQLAlchemy declarative_base, async generators, descriptors with `__set_name__`). Check `.codex/MASTER/PHASE-B/` first.

## References

- [`docs/philosophy.md`](philosophy.md) — why pyfallow exists in this shape
- [`docs/limitations.md`](limitations.md) — what pyfallow does NOT catch (Phase C ticket)
- Full rule reference — Phase C ticket; not yet present as a live docs page
- [`examples/ci/forgejo-actions.yml`](../examples/ci/forgejo-actions.yml) — the workflow template
- [`examples/ci/README.md`](../examples/ci/README.md) — multi-platform CI guide (Forgejo, GitHub, GitLab)
- `pdurlej/platform/AGENTS.md` — identity-isolation, 3+3 canary review (governance context)
- a dogfood log (template at [`docs/dogfood-log-template.md`](dogfood-log-template.md)) — log template for evidence collection

---

*Maintained by Claude Opus 4.7 under operator direction. Updates flow through normal PR review.*
