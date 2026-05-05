# 0006 — Dogfood-first, Show-HN-later (anti-AI-slop)

**Date:** 2026-05-04
**Status:** accepted
**Authors:** operator (`pdurlej`) — decision-maker; Claude Opus 4.7 — recording

## Context

Pre-decision plan (orchestrator's draft) was: Phase A → Phase B (engineering hardening) → Phase C (Show HN polish) → Show HN within ~2 weeks. Tickets in `.codex/MASTER/PHASE-B/` and `PHASE-C/` were ready for Codex execution.

Operator pushed back with strategic redirection during chat 2026-05-04 (transcribed):

> "zdecydowanie jestem vibe coderem, który musi to przetestować. Musimy sami zrobić dogfooding i wrzucić do tego tematu za miesiąc czy dwa w takim tempie kodowania. I tutaj poprosić wszystkich agentów, którzy współpracują na platformie, żeby zrobili audyt i uważają, że pyfallow naprawdę im pomaga. Jeśli tak, super. Jeśli nie, niefajnie. (...) Jest teraz bardzo dużo AI-slopu, a my nie chcemy już chcemy AI-slopowo zrobić naprawdę perełkę."

Translation: "I'm a vibe coder who has to test this. We need to dogfood ourselves first, come back to it in a month or two at this coding pace. Ask all agents working on the platform to audit, see if pyfallow actually helps them. If yes, great. If not, not-so-great. (...) There's a lot of AI-slop right now and we don't want to AI-slop our way to a real gem."

Plus the operator's **founding principle** (recorded earlier same day, also transcribed):

> "Skoro wiemy, że jestem nietechnicznym produktowcem to musimy jak najwięcej inwestować właśnie w takie govern statyczne, deterministyczne rzeczy żebym nie odpierdolał głupot i żebyście wy nie odpierdolali głupot pod moją komendą."

Translation: "Given that I'm a non-technical product person, we need to invest as much as possible in static, deterministic governance — so I don't ship stupidities and so you (agents) don't ship stupidities under my command."

## Decision

**Phase B and Phase C execution is paused** until real-world dogfood evidence accumulates from pyfallow integration into operator's other repos.

**Window:** 2026-05-04 → ~2026-06-15 (4-6 weeks, re-evaluated at end).

**During the window:**
- Pyfallow `0.3.0a2` is integrated as a Forgejo Actions gate in operator's repos: `pdurlej/platform` first (via PR #71 on platform), then `hermes-agency`, `iskra-openclaw`, etc., as appetite allows.
- Each platform / project Codex commit runs through `pyfallow analyze`. Findings are surfaced via PR comments and uploaded artifacts.
- Operator and agents collect real findings — true positives, false positives, friction, missed structural bugs — in a dogfood log per the template at `docs/dogfood-log-template.md`. Each project keeps its own log in its working-notes directory (gitignored, e.g., `.codex/DOGFOOD-LOG.md`).

**At end of window:**
- Operator + orchestrator + Codex read the accumulated logs.
- Phase B/C tickets (Forgejo issues #4-#25) are re-prioritized based on evidence:
  - Tickets validated by repeated FP / TP findings stay (and refined per evidence)
  - Tickets contradicted or made obsolete get closed with rationale
  - New issues open with `dogfood:*` labels (e.g. `dogfood:fp` for confirmed FPs requiring framework heuristic work)
- Only after this re-prioritization does Codex execute on Phase B / C work.
- Show HN remains paused until the dogfood evidence is strong enough to claim "real users (multi-agent operator workflows in this case) have used pyfallow for N weeks and here are the data."

## Consequences

**Positive:**
- Avoids polishing from imagination. Phase B/C planning is good but synthetic; real evidence may invalidate, refine, or add tickets we haven't thought of.
- Aligns with operator's founding principle (deterministic gates for non-technical orchestrator) — pyfallow becomes the **proof** for that principle, not a marketing artifact.
- Anti-AI-slop posture is the differentiator on Show HN day. Distinguishes pyfallow from the flood of AI-tooling slop currently being pushed.

**Negative:**
- Show HN is delayed by ~4-6 weeks at minimum. Risk: another tool occupies the niche. Tradeoff accepted: real evidence > first-mover at the cost of believability.
- Phase B/C planning effort (already invested in `.codex/MASTER/`) stays "in storage" longer. May need refresh if dogfood evidence reorders priorities.
- Operator must remember to actually log dogfood evidence. Orchestrator added a calendar reminder protocol via Iskra Inbox notatka.

**Neutral:**
- This decision is **the right one** for an operator-launched OSS project where the operator is non-technical. Building credibility through real evidence is more compounding than launch hype.

## References

- Iskra Inbox notatka: `00 Inbox/2026-05-04 — Pyfallow Phase A merged + dogfood pivot.md`
- Documentation: `docs/philosophy.md` (founding principle quoted), `docs/dogfood.md` (concrete integration steps), `docs/dogfood-log-template.md` (evidence template)
- Forgejo issues #4-#25 — Phase B/C tickets (status: `phase:b` / `phase:c` labels, in storage until evidence)
- Connection to broader thesis: see `00 Inbox/2026-05-04 — Reverse LM Arena + AI Operator Score (pomysł).md` if it persisted between sessions; pyfallow + dogfood log = evidence for the "non-tech PM + AI agents = quality" thesis
