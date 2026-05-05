# 0008 — Phase B/C execution gated on dogfood evidence

**Date:** 2026-05-04
**Status:** accepted
**Authors:** operator (`pdurlej`) — direction; Claude Opus 4.7 — recording
**Related:** ADR 0006 (dogfood pivot), ADR 0007 (deterministic gate identity)

## Context

After Phase A landed (5 atomic commits, 22 ship-blocker findings resolved), the orchestrator had ready-to-execute briefs for:
- **Phase B**: 12 engineering hardening tickets (Tarjan iterative, walrus, framework FPs, schema drift, etc.)
- **Phase C**: 10 Show HN polish tickets (README revamp, FAQ, public evidence, rule reference, etc.)

These plans live in `.codex/MASTER/PHASE-B/` and `PHASE-C/` (gitignored, working notes). They were prepared **synthetically** based on audit findings — the audit was conducted on a synthetic slop fixture and on pyfallow's own self-analysis. They are **not** based on real-world usage.

ADR 0006 established the dogfood-first strategy. This ADR formalizes the **execution gating mechanism** — what triggers Phase B/C work and how priorities flow from evidence.

## Decision

Phase B and Phase C tickets are migrated to **Forgejo issues** (`pdurlej/pyfallow` issues #4-#25, labels `phase:b` / `phase:c` plus severity + area) so they're discoverable from the project board and don't disappear with session context.

Tickets remain **open but unstarted** until the dogfood window closes (~2026-06-15, re-evaluated at that date). During the window:

1. Pyfallow is integrated into operator's other repos as a Forgejo Actions gate (first integration: `pdurlej/platform` PR #71)
2. Each project's daily Codex/operator workflow accumulates evidence in a `.codex/DOGFOOD-LOG.md` (gitignored per `docs/dogfood-log-template.md`)
3. **Phase B/C tickets do not get worked on**, even if Codex has spare capacity. Polishing from imagination defeats the purpose.

At end of window, evidence triages tickets:

| Evidence | Effect on ticket |
|---|---|
| Multiple `[TP]` log entries matching the ticket's hypothesis | Ticket validated → execute as planned |
| Multiple `[FP]` log entries matching the ticket's hypothesis | Ticket validated AND high priority |
| Single instance with no recurrence | Ticket sample-size-1, lower priority |
| `[FN]` log entries (missed structural bugs) | New ticket created; may pre-empt existing Phase B work |
| `[FRICTION]` log entries | New tickets in Phase C area; may pre-empt existing Phase C polish |
| No log entries on this concern | Ticket descoped or closed (was a synthetic concern) |

After triage, Codex executes a fresh wave of master prompts based on the **re-prioritized** ticket set, not the original list as captured in May 2026.

## Consequences

**Positive:**
- Forces evidence-driven engineering. Avoids the trap of "we have plans, we should execute the plans" without verifying the plans are still relevant.
- Issues are public (well, `pdurlej/pyfallow` is private but visible to the operator's own contributing identities) and reference-able from PR descriptions, dogfood log entries, etc.
- New observations during dogfood window can open new issues that compete for priority with Phase B/C tickets on equal footing.

**Negative:**
- 4-6 weeks of "plans in storage." Risk: planning effort decay. Mitigation: briefs are written down (`.codex/MASTER/`) and cross-referenced from issue bodies; no work is lost, just deferred.
- Operator must actually do the dogfood logging. Mitigation: documented protocol, calendar reminder via Iskra Inbox notatka.

**Neutral:**
- Issue migration was carried out by `claude` (orchestrator) on 2026-05-05 using a Python script (`/tmp/issue_migration.py`) calling Forgejo API with claude PAT. 22 issues created (#4-#25). Each issue body links to the local `.codex/MASTER/PHASE-?/...` brief and explains the dogfood gating.

## References

- Forgejo issues #4-#15 (Phase B), #16-#25 (Phase C)
- `.codex/MASTER/PHASE-B/B*.md`, `PHASE-C/C*.md` — local briefs (gitignored)
- `docs/dogfood-log-template.md` — evidence collection protocol
- ADR 0006 — strategic context (dogfood-first decision)
- ADR 0007 — pyfallow's identity that informs ticket scope checks
- Migration script: `/tmp/issue_migration.py` (transient; operation logged here)
