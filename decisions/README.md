# Architecture Decision Records (ADRs)

This directory holds numbered, immutable architecture decisions for `pyfallow`. Pattern adapted from Michael Nygard's [Documenting architecture decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) and the convention used in `pdurlej/platform/decisions/`.

## Conventions

- One file per decision: `NNNN-short-kebab-title.md`
- Numbering is monotonic and never reused (deprecated/superseded ADRs stay; their status changes)
- Status: `proposed` / `accepted` / `deprecated` / `superseded by NNNN`
- Each ADR has fixed sections: **Status** / **Context** / **Decision** / **Consequences**
- ADRs are written **as decisions are made**, not retrofitted from memory
- Changes to an ADR's intent require a new ADR that supersedes the old one (never edit history)

## Why ADRs (vs. `.codex/DECISIONS.md` working notes)

`.codex/DECISIONS.md` (gitignored) is **working memory** — operator and orchestrator dumps about specific in-progress choices. It disappears with session context.

`decisions/NNNN-*.md` is **project memory** — decisions that outlive any individual session. In git history. Discoverable by future contributors and agents. Reviewable like code.

When a decision in `.codex/DECISIONS.md` matures (settled, applied, observable in the codebase), it migrates here as a numbered ADR. Original working note in `.codex/` may stay as the prep, but the canonical record is here.

## Index

| # | Title | Status |
|---|-------|--------|
| 0001 | [Classification namespace = underscore](0001-classification-namespace-underscore.md) | superseded by 0009 |
| 0002 | [Baseline JSON validation raises ConfigError](0002-baseline-validation-config-error.md) | accepted |
| 0003 | [Forgejo runner = ubuntu-latest, not docker:python](0003-forgejo-runner-ubuntu-latest.md) | partially superseded by 0011 |
| 0004 | [Test `normalize()` handles FastMCP dataclass wrapping](0004-test-normalize-dataclass-branch.md) | accepted |
| 0005 | [Alpha-incremental release strategy](0005-alpha-incremental-release.md) | accepted |
| 0006 | [Dogfood-first, Show-HN-later (anti-AI-slop)](0006-dogfood-pivot-anti-slop.md) | accepted (transcription corrected 2026-05-05) |
| 0007 | [Pyfallow as bassist (counterpart to platform.exe; harness, not agent)](0007-pyfallow-as-deterministic-gate.md) | accepted (metaphor refined 2026-05-05) |
| 0008 | [Phase B/C execution gated on dogfood evidence](0008-phase-b-c-evidence-gated.md) | accepted (evidence-bounded refinement 2026-05-05) |
| 0009 | [Three-bucket classification with mandatory product-language explanations](0009-three-bucket-classification.md) | accepted |
| 0010 | [Mandatory non-author AI reviewer + branch protection on every PR](0010-mandatory-non-author-reviewer.md) | accepted |
| 0011 | [Adopt Forgejo-native CI pattern (from parallel Codex thread's stash)](0011-forgejo-native-ci-pattern.md) | accepted |
