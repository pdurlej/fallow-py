# AGENTS.md — Repo Runbook for Agents

**Audience:** orchestrator (`claude` — Pan Herbata / Claude Opus 4.7), producer (`codex` — Codex CLI), reviewers (3+3 ensemble: claude/codex/glm × tech/product), operator (`pdurlej`) reads as observer.

**Purpose:** reduce low-quality iterations from missing context. If you're an agent acting on this repo — **read this first**. The rules here override defaults.

**Pattern source:** mirrors `pdurlej/platform/AGENTS.md` (see ADR 0010 in `decisions/0010-mandatory-non-author-reviewer.md` and platform issue #75 for the global escalation). Microproject-local rules **add**, never subtract from platform contract.

---

## What this repo is

`pdurlej/pyfallow` (git.pdurlej.com primary; github.com/pdurlej/pyfallow mirror) is a **deterministic Python static analyzer** that AI agents call on themselves before commit. The thesis (per ADR 0006, ADR 0007, `docs/philosophy.md`):

> Pyfallow is the **bassist** for the AI-agent band. Iskra is the vocalist (relational, memory-rich, makes the band's voice). Codex is the drummer (rhythm + execution). Claude / Opus is the lead guitarist (orchestrating, articulating). Pyfallow is bassist — disciplined background member, holds the rhythm, lets the vocalist and lead shine. **Without bassist, the band sounds empty; with bassist, audience often doesn't notice the bassist — and that's part of the role.**

Pyfallow is a **harness** (deterministic tool), not an **agent** (reasoning, opinion-having entity). Categorical distinction enforced.

The repo holds:

- **Core analyzer** in `src/pyfallow/` — 28 modules, stdlib-only Python ≥3.11
- **MCP server** in `mcp/src/pyfallow_mcp/` — separate package, FastMCP + Pydantic v2
- **Tests** in `tests/` (core) and `mcp/tests/` (MCP)
- **CI workflows** in `.forgejo/workflows/` (primary) and `.github/workflows/` (mirror)
- **Architecture decisions** in `decisions/` — numbered ADRs (Nygard format)
- **User-facing docs** in `docs/` — philosophy, dogfood guide, limitations, etc.
- **Templates + benchmarks** in `examples/` and `benchmarks/`
- **Working notes (gitignored)** in `.codex/` — orchestrator's planning, Phase B/C briefs, handoffs, dogfood log

**This repo is operator-owned.** Operator (`pdurlej`) is the merger; orchestrator is PM; Codex is producer; 3+3 ensemble are reviewers. See ADR 0010 for the role formalization.

---

## Current phase

**Post-Phase-A, dogfood window open** (ADR 0006, ADR 0008).

Phase A (5 ship-blocker tickets A1-A5) merged on `main` via PR #2 on 2026-05-04. TestPyPI has `pyfallow 0.3.0a2` and `pyfallow-mcp 0.1.0a2`.

**Phase B (12 issues #4-#15) and Phase C (10 issues #16-#25) are PAUSED** until dogfood evidence accumulates. Window is **evidence-bounded, not time-bounded** (ADR 0008 evidence-bounded refinement). Triage triggers when:
- ≥100 pyfallow CI runs across integrated repos, AND
- ≥20 dogfood log entries with non-`[FRICTION]`-only category breakdown, AND
- Operator's qualitative read that the evidence is sufficient

Until that threshold, Codex does **not** execute on Phase B/C tickets. Working on them anyway is process violation — surfaces as a blocked PR review.

Active work: dogfood integration into operator's other repos (`pdurlej/platform`, `hermes-agency`, `iskra-openclaw`, ...) and infrastructure for evidence collection (issue #29: cron aggregator on rs2000).

---

## Conventions

### Identity-isolation (per platform AGENTS.md § Identity-isolation)

Every actor has a separate Forgejo identity + PAT (in BW under `git.pdurlej.com (<actor>)` items, custom field `PAT`):

- **`claude`** (orchestrator, this prose; user id 3 on Forgejo)
- **`codex`** (producer; user id from platform's setup, see platform AGENTS.md)
- **`glm`** (z.ai reviewer; when present)
- **`pdurlej`** (operator; user id 1; merge gate)

When an agent commits / pushes / opens PRs, it MUST use its own identity:

```bash
# Set git config in worktree:
git config user.email "<actor>@noreply.git.pdurlej.com"
git config user.name "<actor>"

# Push with PAT (extract from BW custom field):
ACTOR_PAT=$(bw get item "git.pdurlej.com (<actor>)" | python3 -c "
import json, sys
item = json.load(sys.stdin)
for f in item.get('fields', []):
    if f.get('name') == 'PAT': print(f['value'])
")
git -c http.extraheader="Authorization: token $ACTOR_PAT" push

# PR creation via Forgejo API:
curl -sX POST -H "Authorization: token $ACTOR_PAT" -H "Content-Type: application/json" \
  https://git.pdurlej.com/api/v1/repos/pdurlej/pyfallow/pulls -d @pr-body.json
```

**Anti-pattern:** pushing as operator (`pdurlej`) when you are claude/codex/glm. Audit trail lies. Caught in pyfallow PR #2 comment review 2026-05-04 (Klaud's first comment was posted as `pdurlej` via shared MCP, deleted and reposted as `claude` per identity isolation).

### Mandatory non-author reviewer (ADR 0010)

**Every PR**, regardless of size class, requires ≥1 approved review from a contributor different from the PR author. Reviewer can be an AI agent (default rotation: claude reviews codex, codex reviews claude; glm joins as third when available). Operator-as-reviewer is escape valve only — operator's primary role is merge button.

Branch protection rule on `main` mechanically enforces:
- Direct push to `main` blocked (whitelist empty; PR-only)
- ≥1 approved review required, stale dismissed on new commits
- Required status checks (CI / Python 3.11/3.12/3.13 (pull_request)) must pass green
- Branch up-to-date with `main` before merge
- Force-push blocked
- **Rule applies to repo administrators** (operator subject; break-glass = explicit "disable rule, push, re-enable" with audit trail)

The rule was enabled by operator on 2026-05-05 via Forgejo Settings UI. Live test: PR #30 (`decisions/post-operator-review-2026-05-05`) was the first PR governed by the new rule.

### PR size classes (per platform AGENTS.md § PR size classes)

| Size | Definition | Review | Iter cap | Context Pack |
|---|---|---|---|---|
| Small | Single file, docs-only, narrow non-runtime; no security/deploy/restore/exposure change | 1 reviewer (any role); iter cap 1 | 1 (unless HIGH/CRITICAL) | Shortened: product story + what changed + why safe lightly |
| Medium | Touches CI, runtime evidence, recovery notes, exposure classification, schema, multi-file refactor | Full canary 3+3 | 3 (hard) | Full pack |
| Large | ADR, governance doc, platform.exe-equivalent, restore path, deploy semantics, security boundary, workflow rule, multi-subsystem | Full canary 3+3; owner-facing in Owner Action Board | 3 (hard) | Full pack |
| Batch | Multiple Small PRs from same wave / bounded path | Light per-PR + Night Review | per-PR 1; batch 1 | Per-PR shortened |

**Rule:** PR sharding does NOT bypass review. Accumulated small changes → Night Review.

### Canary Context Pack (required for Medium/Large PRs)

```markdown
## Canary Context Pack

### Product story
What are we trying to make true for the operator/user, and why?

### What changed
Concrete summary of the change.

### Why it changed
Reason this change exists now.

### Files touched
List of relevant files.

### Relevant context
ADRs, module docs, subsystem docs, related manifests.

### Runtime evidence
Test runs, CI evidence, build verification if relevant.

### Known constraints
What the reviewer must not assume.

### Explicit out-of-scope
What this PR intentionally does not solve.

### Requested decision
What review outcome is being requested.

### Merge blockers
What would block merge.
```

Reviewers read **product-first and operator-first**, not only diff-first.

### Owner Action Board (required for owner-facing reports)

Every State of Pyfallow / strategic stop / multi-decision report MUST start with:

```markdown
## Owner Action Board

### Needs owner now
- CLICK: <action>
- CHOOSE: <decision with default>

### Default path unless owner objects
- DEFAULT: <will-proceed-unless-objected>

### Agent follow-up, no owner attention now
- TASK: <create issue/PR>

### Blocked / waiting on precondition
- BLOCKED: <thing> until <condition>
```

Owner-facing question: "does this need Piotr's attention now, yes or no?" Verbs: CLICK / CHOOSE / DEFAULT / TASK / BLOCKED. Simple. Mobile-scannable.

### Model / emotional signal note (≤280 chars)

Directly below Owner Action Board. NOT therapy or self-justification. Compressed hidden-signal channel: what does the model/orchestrator sense about product, process, risk, ambiguity that operator may not see directly?

Example: `Yellow→green. Phase A grew from "fix some bugs" to "global governance pattern" via operator's voice review. Risk: drift if 4-PR queue stays open without codex review rotation. Mitigation: AGENTS.md (this file) is the rotation plumbing.`

---

## What an agent must NOT infer without runtime evidence

- **Fingerprint stability across runs**: don't assume; verify with `pyfallow analyze --format json` twice and compare.
- **Classification semantics**: don't trust your memory; read `src/pyfallow/classify.py` and `decisions/0001-*.md` + `decisions/0009-*.md`.
- **Test coverage on a module**: don't assume covered if file exists in `tests/`; check actual collection (`pytest --co tests/test_<module>.py`).
- **Forgejo runner availability**: don't assume rs2000 is up; verify via Forgejo Actions API or operator confirmation.
- **PyPI vs TestPyPI state**: don't assume any version is current; `pip index versions pyfallow` or curl pypi.org JSON API.
- **MCP wire format on a given pyfallow version**: don't assume namespace; check the installed package's `Classification` model.

---

## Anti-patterns (from cycles up to 2026-05-05)

### "Largest-noise" antipattern

Operator's observation 2026-05-05 (translated, condensed):

> "Agent if asked something will always answer and always strive for the largest possible response and the largest amount of noise to show how important and smart and wonderful it is. (...) Need very firm boundaries so it doesn't create the largest madness. (...) If you look at platform's history of 3+3 canary, it ended in real tragedies — continuous over-elaboration."

**Defenses:**

- **Iteration cap is hard.** 3 iterations max for Medium/Large. After cap → terminal action (`approve_merge`, `defer_to_issue`, `rewrite`, `split_pr`, etc.). Don't iterate forever to perfect the answer. Ship the decision.
- **Brief is the constraint.** A PR brief tells you what's in scope. Reviewer commenting "you should also fix X" where X is out-of-scope = inappropriate. Open a sister issue.
- **Don't volunteer architecture.** When reviewing a typo fix PR, don't propose refactoring the whole module. The PR's job is the typo fix.
- **No opinion-based blocking.** Code style preferences, naming taste, "I would have done it differently" — these are review **comments**, not **blocks**. Block only on objective issues (ADR violation, broken test, security issue, factual error).

### Producer-mode regression (from platform's history)

Pre-canary platform Codex was producing many PRs without canary, ending each turn with options-list, treating amendment iteration as the work itself. Counter-pattern: **canary-first** before opening PR; **answer the question, then stop**.

### Manual-state in prose-only open loops

State that should be in Forgejo Issues (or at minimum auto-derived) lives only in markdown, recreating hidden-state burden. Counter: tickets in issues, decisions in `decisions/`, working notes in `.codex/` (gitignored — that's intentional, working notes are session-bound).

### Calendar-first estimates

Treating time as the axis instead of owner attention units. Counter: estimate in operator-prompts / operator-clicks / operator-decisions; calendar follows from operator availability.

### Truncated digests

Don't truncate file digests, package versions, fingerprints. Always full or `yq`-source from authoritative file. Truncated identifiers fail at consumption time.

### Silently fixing drift

If a contract claims X and observed reality says Y, surface the gap in PR description; default to fix-claim-to-match-reality, but **document the choice**. Hiding drift = silent debt.

### Self-referential ADRs without enforcement mechanism

ADR that says "mandatory" with no enforcement is auto-sabotaging. Pair with inline-enforcement (test, type, branch protection rule) until CI enforcement lands. ADR 0010 is the canonical example: "mandatory non-author reviewer" is enforced by branch protection rule on `main`, not just by convention.

---

## How to request more context

If reviewing and the diff is insufficient:

1. Try the default escalation chain: subsystem files → relevant ADRs → relevant module docs → CI runtime evidence.
2. If still insufficient, return `approve_with_evidence_gap` with explicit gap statement: "Cannot verify <X>; need <runtime evidence Y or document Z>."
3. The PR proceeds only if operator explicitly accepts the gap or moves to a tracked issue.

If executing (Codex/orchestrator) and a master prompt is insufficient:

1. Read referenced ADRs + relevant `decisions/` entries.
2. Read 1-2 example PRs from canary-validated patterns (PR #2 Phase A, PR #71 platform integration, PR #30 governance ADR migration).
3. If still ambiguous, **surface ambiguity with proposed default + consequence + fallback** — do not silently default, do not block on operator without showing your reasoning. Format: "Proposing default X because Y; consequence if wrong is Z; fallback is W. Proceeding unless objected." Operator can object before any irreversible step; until then, don't stall.

---

## When in doubt — defaults (per operator review 2026-05-04 → 2026-05-05)

- Propose a default + state the consequence
- Create/link an issue for follow-up
- Mark the evidence gap explicitly
- Move forward within the iteration cap
- Don't leave important work as prose-only open loops
- Don't make Piotr infer what needs his attention

**Success metric:** less owner ambiguity, more autonomous high-quality progress.

---

## References

- `decisions/` directory — all ADRs (numbered Nygard format); start with README.md for index
- `docs/philosophy.md` — pyfallow's role as bassist + harness (counterpart to platform.exe for code)
- `docs/dogfood.md` — concrete how-to integrate pyfallow into a Forgejo Actions CI in another project
- `docs/dogfood-log-template.md` — evidence collection protocol
- `pdurlej/platform/AGENTS.md` — global pattern source; this file mirrors with pyfallow-specific adaptations
- `pdurlej/platform/PLATFORM_CONSTITUTION.md` — `platform.exe` identity counterpart to pyfallow's identity
- `pdurlej/platform` issue #75 — escalation of mandatory-non-author-reviewer pattern to platform-level governance

---

*Maintained by `claude` (orchestrator). Authored 2026-05-05 per operator's voice request. Updates flow through canary 3+3 review like any other governance change.*
