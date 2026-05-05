# 0006 — Dogfood-first, Show-HN-later (anti-AI-slop)

**Date:** 2026-05-04 (transcription corrected + thesis added 2026-05-05)
**Status:** accepted
**Authors:** operator — decision-maker; Claude Opus 4.7 — recording

> **Edit note 2026-05-05:** Operator-corrected the original Whisper transcription (which was garbled with two contradicting clauses) and added a stronger founding thesis. Decision intent unchanged; the corrected text below is canonical.

## Context

Pre-decision plan (orchestrator's draft) was: Phase A → Phase B (engineering hardening) → Phase C (Show HN polish) → Show HN within ~2 weeks. Tickets in `.codex/MASTER/PHASE-B/` and `PHASE-C/` were ready for Codex execution.

Operator pushed back with strategic redirection during chat 2026-05-04. Operator-corrected canonical version (2026-05-05):

> "Zdecydowanie jestem vibe coderem, który musi to przetestować. Musimy sami zrobić dogfooding i wrzucić do tego tematu za miesiąc czy dwa w takim tempie kodowania. I tutaj poprosić wszystkich agentów, którzy współpracują nad realnymi repozytoriami, żeby zrobili audyt i uważają, że pyfallow naprawdę im pomaga. Jeśli tak, super. Jeśli nie, niefajnie. (...)
>
> Jest teraz bardzo dużo AI-slopu, a my chcemy! **Nie AI-slopowo, czyli myśląc AI-em, używając mądrzej AI-a, zrobić naprawdę perełkę.**"

Translation (operator-corrected): "I'm a vibe coder who has to test this. We need to dogfood ourselves first, come back to it after real usage at this coding pace. Ask all agents working on real repositories to audit whether pyfallow actually helps them. (...) There's a lot of AI-slop right now and we want — not in an AI-slop way, but **by thinking with AI, using AI more wisely** — to make something genuinely a gem."

The original Whisper transcription had garbled the second sentence as "a my nie chcemy już chcemy AI-slopowo" (two contradicting clauses). The corrected version above is canonical.

### Founding thesis (added 2026-05-05)

Subsequent voice review surfaced a stronger formulation that anchors pyfallow's positioning:

> "AI z dyscypliną — zajebista sprawa. AI bez dyscypliny — to jest szum. Signal vs noise nic nie zmienia w historii ludzkości, tylko zmieniają się narzędzia."

Translation: "AI with discipline is a brilliant thing. AI without discipline is noise. Signal vs noise doesn't change in human history — only the tools change."

This is the differentiator. Pyfallow is **not anti-AI**; pyfallow is **the discipline that turns AI from slop into signal**. Bassist (per ADR 0007 edit 2026-05-05) for the AI-agent band. The narrative for Show HN, when it eventually comes, builds on this thesis.

### Window length (clarified 2026-05-05)

Operator clarified the dogfood window is "kilka miesięcy" (several months), not 4-6 weeks as originally drafted. Combined with operator's voice on evidence-bounded triage (recorded in ADR 0008 edit 2026-05-05), the window is no longer time-bounded at all — it ends when sufficient evidence count is reached, not on a calendar date.

Plus the operator's **founding principle** (recorded earlier same day, also transcribed):

> "Skoro wiemy, że jestem nietechnicznym produktowcem to musimy jak najwięcej inwestować właśnie w takie govern statyczne, deterministyczne rzeczy żebym nie odpierdolał głupot i żebyście wy nie odpierdolali głupot pod moją komendą."

Translation: "Given that I'm a non-technical product person, we need to invest as much as possible in static, deterministic governance — so I don't ship stupidities and so you (agents) don't ship stupidities under my command."

## Decision

**Phase B and Phase C execution is paused** until real-world dogfood evidence accumulates from pyfallow integration into operator's other repos.

**Window:** evidence-bounded, not calendar-bounded. See ADR 0008 for the thresholds.

**During the window:**
- Pyfallow `0.3.0a2` is integrated as a Forgejo Actions gate in real operator-owned repositories as appetite allows.
- Each project Codex commit runs through `pyfallow analyze`. Findings are surfaced via PR comments and uploaded artifacts.
- Operator and agents collect real findings — true positives, false positives, friction, missed structural bugs — in a dogfood log per the template at `docs/dogfood-log-template.md`. Each project keeps its own log in its working-notes directory (gitignored, e.g., `.codex/DOGFOOD-LOG.md`).

**At end of window:**
- Operator + orchestrator + Codex read the accumulated logs.
- Phase B/C tickets (Forgejo issues #4-#25) are re-prioritized based on evidence:
  - Tickets validated by repeated FP / TP findings stay (and refined per evidence)
  - Tickets contradicted or made obsolete get closed with rationale
  - New issues open with `dogfood:*` labels (e.g. `dogfood:fp` for confirmed FPs requiring framework heuristic work)
- Only after this re-prioritization does Codex execute on Phase B / C work.
- Show HN remains paused until the dogfood evidence is strong enough to claim real multi-agent workflows have used pyfallow and here are the data.

## Consequences

**Positive:**
- Avoids polishing from imagination. Phase B/C planning is good but synthetic; real evidence may invalidate, refine, or add tickets we haven't thought of.
- Aligns with operator's founding principle (deterministic gates for non-technical orchestrator) — pyfallow becomes the **proof** for that principle, not a marketing artifact.
- Anti-AI-slop posture is the differentiator on Show HN day. Distinguishes pyfallow from the flood of AI-tooling slop currently being pushed.

**Negative:**
- Show HN is delayed until evidence is sufficient. Risk: another tool occupies the niche. Tradeoff accepted: real evidence > first-mover at the cost of believability.
- Phase B/C planning effort (already invested in `.codex/MASTER/`) stays "in storage" longer. May need refresh if dogfood evidence reorders priorities.
- Operator must remember to actually log dogfood evidence. Mitigation: keep the log template lightweight and review it during dogfood triage.

**Neutral:**
- This decision is **the right one** for an operator-launched OSS project where the operator is non-technical. Building credibility through real evidence is more compounding than launch hype.

## References

- Documentation: `docs/philosophy.md` (founding principle quoted), `docs/dogfood.md` (concrete integration steps), `docs/dogfood-log-template.md` (evidence template)
- Forgejo issues #4-#25 — Phase B/C tickets (status: `phase:b` / `phase:c` labels, in storage until evidence)
- Broader thesis: pyfallow + dogfood log = evidence for the "non-tech PM + AI agents = quality" thesis
