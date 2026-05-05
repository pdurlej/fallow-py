# 0010 — Mandatory non-author AI reviewer + branch protection on every PR

**Date:** 2026-05-05
**Status:** accepted
**Authors:** operator (`pdurlej`) — decision-maker; Claude Opus 4.7 — recording
**Related:** ADR 0006 (anti-AI-slop posture), ADR 0007 (deterministic gate identity), `pdurlej/platform` issue #75 (escalation to global pattern)

## Context

During Phase A close-out review (chat 2026-05-05 ~05:15), operator surfaced a process gap that the Phase A retrospective hadn't named explicitly:

In Phase A ticket A4 (Python 3.11 MCP test fix), Codex saw 9 of 13 MCP tests failing on Python 3.11 in the GitHub CI matrix and just fixed them locally, then committed. **There was no escalation to operator that the entire 3.11 matrix had been silently red.** Reactive fix, not defensive escalation.

Operator's framing (voice translated, lightly cleaned):

> "Why aren't you noticing? Why aren't you escalating CI problems to me? It should be hitting me immediately during reviews that without that — you can't merge this. But because you have… nobody cares about merges except me. Because I have to merge and only I can merge, that effectively means none of you (agents) care about these things.
>
> This is bad. We should make it so that someone else is the reviewer — I am still the merger, sure, but someone else has to review. There should be at least one reviewer always. We had something like this in platform with the 3+3 canary pattern for medium-sized changes. But this should also apply to small changes — there has to be at least one reviewer (code, product, technology — whatever fits) without whose approval the change cannot move forward. Without their approval, CI/CD shouldn't let it through.
>
> The way platform builds code should be the universal source for all microprojects."

And on whether the reviewer can be an AI agent:

> "Yes, exactly. It can be an AI agent. No, no, no, there's no other human besides me. It has to be an AI agent that's not the author — different perspective always. Default rotation: claude and codex. You guys love each other; you'll grow even fonder."

## Decision

**Mandatory non-author reviewer on every PR**, applied uniformly across all of operator's microprojects (`pyfallow`, `hermes-agency`, `iskra-openclaw`, ...) with the platform repo's `AGENTS.md` as canonical contributor contract.

Specifically:

1. **Every PR** — regardless of size class (Small / Medium / Large / Batch per platform's existing taxonomy) — requires ≥1 approved review from a contributor **different from the PR author**.

2. **Reviewer can be an AI agent.** Default rotation: `claude` reviews `codex`'s PRs; `codex` reviews `claude`'s PRs; `glm` reviews when available as a third-party perspective. **Identity-isolation enforced** — the reviewer's commits must come from a different PAT and different commit author than the PR's commits.

3. **Branch protection rule on `main`** mechanically enforces:
   - Direct push to `main` blocked (whitelist empty; PR-only)
   - ≥1 approved review required
   - Stale approvals dismissed when new commits pushed
   - Required status checks (per-project CI matrix) must pass green
   - Branch must be up-to-date with `main` before merge
   - Force-push blocked
   - **Rule applies to repository administrators** — operator subject to same rules; break-glass = explicit "disable rule, push, re-enable" with audit trail in repo settings history

4. **Operator (`pdurlej`) is the merger**, not a reviewer-of-record. Operator's role: final approval and merge button. Review work is delegated to AI agents per identity-isolation policy.

5. **Platform's `AGENTS.md` is canonical contributor contract** for every microproject. Microproject-local docs (e.g., `pdurlej/pyfallow/.codex/WORKFLOW.md`) may add project-specific extras; never subtract from platform contract.

## Pyfallow as first integration

Branch protection rule on `pdurlej/pyfallow/main` enabled by operator via Forgejo Settings UI on 2026-05-05 (operator action immediately following the voice review that produced this decision). Configuration:

- Push to `main`: whitelist empty (no direct push)
- Required approving reviews: 1
- Dismiss stale approvals on new commits: yes
- Required status checks:
  - `CI / Python 3.11 (pull_request)`
  - `CI / Python 3.12 (pull_request)`
  - `CI / Python 3.13 (pull_request)`
- Require up-to-date branch: yes
- Block merge on rejected reviews: yes
- Block merge if PR is out-of-date: yes
- Enforce for admins: yes
- Allowed mergers (whitelist): `pdurlej` only

This ADR's PR itself (`decisions/post-operator-review-2026-05-05`) is the **first PR governed by the new rules** — meta-validation that the rule works in practice.

## Escalation to platform

Pattern is escalated to platform repo as proposal: [`pdurlej/platform` issue #75](https://git.pdurlej.com/pdurlej/platform/issues/75) — universal source of truth in platform's `AGENTS.md`, with branch protection on every microproject inheriting from there. That issue tracks the platform-side amendment (full Canary 3+3 review per existing platform governance).

## Consequences

**Positive:**
- Phase A's silent 3.11-CI-red incident becomes structurally impossible. Codex (or any agent) cannot merge a PR with broken matrix without claude (or another non-author agent) approving — and approving requires looking at CI output, which surfaces the redness.
- Operator stops being the de-facto reviewer-of-record. Operator role narrows to merger + strategic-decisions, freeing operator's attention.
- AI-agent-as-reviewer is structurally enabled, validating ADR 0007's "harness vs agent" distinction — agents have meaningful collaborative roles, not just executor roles.

**Negative:**
- **AI agents can rubber-stamp each other.** Mitigation: AGENTS.md spec for reviewer responsibility (must read CI output, must read diff, must articulate review reasoning in PR comment — not just "approve" without context). Phase B Issue (forthcoming) tracks reviewer-quality measurement.
- **Solo agent scenarios block.** If only `claude` is available and `claude` is the author, no non-author AI agent exists. Mitigation: operator escalation-of-last-resort. Operator can review-then-merge in this case, treating their own review as the non-author review (operator is *not* the author by definition).
- **Bootstrap problem for new microprojects.** First PR on a new microproject has no prior reviewers configured. Mitigation: branch protection rule template applied at repo creation (per platform issue #75 rollout).

**Neutral:**
- Codex's behavior in Phase A A4 was reactive-not-defensive but it was not malicious. Codex did fix the bug; the gap was process-level (no requirement to escalate). The new rule structurally fixes the process; no individual-agent blame.

## References

- Operator voice transcription, 2026-05-05 ~05:15 (recorded in this ADR's Context section)
- Phase A ticket A4 (commit `527865e`) — incident that surfaced the gap
- ADR 0006 — anti-AI-slop strategic context
- ADR 0007 — pyfallow as deterministic gate; this ADR is the process companion
- `pdurlej/platform` issue #75 — escalation to platform-level governance amendment
- `pdurlej/platform/AGENTS.md` § Canary 3+3 review — current scoping (this ADR extends to universal floor)
