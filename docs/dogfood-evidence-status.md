# Dogfood Evidence Status

**Status:** active dogfood window after the `fallow-py` public rename.

This page is the durable, public pointer for what happens before Phase B/C work resumes.
It prevents the current plan from living only in chat context.

## Current State

- Canonical repo name: `pdurlej/fallow-py`.
- Current alpha: `fallow-py 0.3.0a3` and `fallow-py-mcp 0.1.0a3`.
- Phase B/C engineering issues remain open but paused by ADR 0008.
- DeepSeek audit triage is indexed in [Forgejo #35](https://git.pdurlej.com/pdurlej/fallow-py/issues/35) and summarized in [`docs/audits/deepseek-v4-pro-triage-2026-05-12.md`](audits/deepseek-v4-pro-triage-2026-05-12.md).
- Dogfood aggregation infrastructure is tracked in [Forgejo #29](https://git.pdurlej.com/pdurlej/fallow-py/issues/29).

## Evidence Gate

Phase B/C work resumes when the operator has enough real-world signal, not when a
calendar date passes. The current gate is:

- at least 100 fallow-py CI runs across integrated repositories,
- at least 20 meaningful dogfood log entries, and
- the operator's qualitative read that the evidence is enough to prioritize work.

## Immediate Next Work

1. Integrate fallow-py CI into operator-owned Python repositories.
2. Log false positives, useful findings, missed findings, and workflow friction with [`docs/dogfood-log-template.md`](dogfood-log-template.md).
3. Keep accepted DeepSeek follow-ups visible through Forgejo issues instead of re-litigating the raw audit.
4. Treat `fallow-ts` as a sibling project, not a reason to expand this Python analyzer before evidence arrives.

## Operator Action Items

- Set Forgejo repository topics to match GitHub: `python`, `static-analysis`,
  `code-intelligence`, `ai-agents`, `sarif`, `dead-code`, `architecture`,
  `dependency-analysis` ([Forgejo #49](https://git.pdurlej.com/pdurlej/fallow-py/issues/49)).
- Decide when `0.3.0a3` should become an actual GitHub/TestPyPI release artifact
  ([Forgejo #50](https://git.pdurlej.com/pdurlej/fallow-py/issues/50)).
