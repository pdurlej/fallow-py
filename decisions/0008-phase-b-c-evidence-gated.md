# 0008 — Phase B/C execution gated on dogfood evidence

**Date:** 2026-05-04 (window definition refined 2026-05-05)
**Status:** accepted
**Authors:** operator — direction; Claude Opus 4.7 — recording
**Related:** ADR 0006 (dogfood pivot), ADR 0007 (bassist metaphor / harness identity), ADR 0010 (mandatory non-author reviewer)

> **Edit note 2026-05-05:** Original draft fixed the dogfood window to 2026-05-04 → 2026-06-15 (4-6 weeks). Operator review surfaced that **time is the wrong axis** — what matters is evidence count, not calendar date. This edit replaces fixed-date window with evidence-bounded definition and records the need for lightweight aggregation infrastructure.

## Context

After Phase A landed (5 atomic commits, 22 ship-blocker findings resolved), the orchestrator had ready-to-execute briefs for:
- **Phase B**: 12 engineering hardening tickets (Tarjan iterative, walrus, framework FPs, schema drift, etc.)
- **Phase C**: 10 Show HN polish tickets (README revamp, FAQ, public evidence, rule reference, etc.)

These plans live in `.codex/MASTER/PHASE-B/` and `PHASE-C/` (gitignored, working notes). They were prepared **synthetically** based on audit findings — the audit was conducted on a synthetic slop fixture and on pyfallow's own self-analysis. They are **not** based on real-world usage.

ADR 0006 established the dogfood-first strategy. This ADR formalizes the **execution gating mechanism** — what triggers Phase B/C work and how priorities flow from evidence.

## Decision

Phase B and Phase C tickets are migrated to **Forgejo issues** (issues #4-#25, labels `phase:b` / `phase:c` plus severity + area) so they're discoverable from the project board and don't disappear with session context.

Tickets remain **open but unstarted** until the evidence-bounded dogfood window closes. During the window:

1. Pyfallow is integrated into real repositories as a Forgejo Actions gate.
2. Each project's daily Codex/operator workflow accumulates evidence in a `.codex/DOGFOOD-LOG.md` (gitignored per `docs/dogfood-log-template.md`)
3. **Phase B/C tickets do not get worked on**, even if Codex has spare capacity. Polishing from imagination defeats the purpose.

## Evidence-bounded window (refined 2026-05-05)

Operator's voice 2026-05-05:

> "W zależności od tego jak dużo tokenów spalę, będziemy w stanie określić, jak szybko wyśliemy sobie, że pyfallow dobrze działa. Jeśli spalę setki tysięcy tokenów, to będziemy wiedzieli dość dobrze. Jeśli będę bardzo mało używał, to nie będziemy wiedzieli czy działa. Tutaj chodzi o liczbę logów. Powinniśmy zależeć nie od czasu."

Translation: "Depending on how many tokens I burn, we'll be able to determine how quickly we know pyfallow works. If I burn hundreds of thousands of tokens, we'll know pretty well. If I use very little, we won't know if it works. It's about the number of logs. We should depend not on time."

The window has **no fixed end date**. Window closes when **sufficient evidence count** is reached — measured by:

1. **Number of pyfallow CI runs across integrated repos** — proxy for how many opportunities pyfallow had to surface findings
2. **Number of dogfood log entries** of class `[TP]`, `[FP]`, `[FN]`, or `[FRICTION]` — proxy for how many findings were notable enough to record
3. **Token spend on pyfallow-gated commits** — proxy for operator's actual usage intensity

Loose threshold (re-evaluated as evidence accumulates): when there are **at least 100 pyfallow CI runs total across all integrated repos AND at least 20 dogfood log entries** with category breakdown that's not dominated by `[FRICTION]` only (we want to see real `[TP]`/`[FP]` signal), the orchestrator + operator do the triage session.

If after several months no integrated repo accumulates that volume, that itself is evidence: pyfallow isn't getting enough use to claim usefulness. Different decision required (drop project, pivot, or restart with more aggressive integration).

## Infrastructure dependency

Evidence collection requires aggregation infrastructure. Operator's decision (voice 2026-05-05): use a lightweight scheduled job on the existing CI infrastructure.

Cron job specs (tracked as Forgejo issue #29):
- Weekly schedule (Sunday 04:00 — operator-attention-friendly)
- Fetches all completed pyfallow CI workflow runs across operator's integrated repos
- Downloads `pyfallow-report.json` artifacts
- Aggregates findings by rule, by repo, by week-over-week trend
- Posts as comment on a separate Forgejo issue tagged `pyfallow-dogfood-evidence-inbox` (ever-open issue, single source of truth for aggregated evidence)
- Identity: scheduled job runs under an actor-scoped automation identity from the approved secret store

Without this aggregator, evidence collection becomes 30+ artifact downloads after months of dogfood = friction = operator skips analysis = decision blind. With aggregator, evidence is delivered ready-to-read.

Implementation lands within first 2-3 weeks of dogfood window opening (i.e., before evidence really accumulates and the manual aggregation pain becomes acute).

## Triage trigger

When the evidence threshold is reached, evidence triages tickets:

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
- Issues are reference-able from PR descriptions, dogfood log entries, etc.
- New observations during dogfood window can open new issues that compete for priority with Phase B/C tickets on equal footing.

**Negative:**
- Several months of "plans in storage." Risk: planning effort decay. Mitigation: briefs are written down (`.codex/MASTER/`) and cross-referenced from issue bodies; no work is lost, just deferred.
- Operator must actually do the dogfood logging. Mitigation: cron aggregator (issue #29) plus lightweight reminders.
- Evidence-bounded means uncertainty: we don't know in advance when window closes. Mitigation: weekly cron aggregation gives operator a continuous read on accumulated evidence; threshold judgment can be made any week.

**Neutral:**
- Issue migration was carried out by `claude` (orchestrator) on 2026-05-05 using a transient local script and actor-scoped Forgejo API credentials. 22 issues created (#4-#25). Each issue body links to the local `.codex/MASTER/PHASE-?/...` brief and explains the dogfood gating.

## References

- Forgejo issues #4-#15 (Phase B), #16-#25 (Phase C)
- `.codex/MASTER/PHASE-B/B*.md`, `PHASE-C/C*.md` — local briefs (gitignored)
- `docs/dogfood-log-template.md` — evidence collection protocol
- ADR 0006 — strategic context (dogfood-first decision)
- ADR 0007 — pyfallow's identity that informs ticket scope checks
- Migration script: transient local script; operation logged here
