# DeepSeek v4 Pro Audit Triage - 2026-05-12

DeepSeek v4 Pro produced a broad fallow-py repository audit on 2026-05-11/2026-05-12.
This note records the human/Codex triage result. The raw audit is useful input, not an
architecture decision and not an accepted backlog by itself.

The durable backlog index is Forgejo issue
[#35](https://git.pdurlej.com/pdurlej/fallow-py/issues/35).

## ADR Context Checked

- ADR 0008 keeps Phase B/C execution gated on dogfood evidence.
- ADR 0009 accepts the three-bucket classification model, but explicitly defers
  implementation to Forgejo
  [#27](https://git.pdurlej.com/pdurlej/fallow-py/issues/27) / B13.
- Therefore the current `manual_only` implementation is not treated as a silent P0 bug in
  this triage. It is accepted design work that remains intentionally deferred.

## Accepted Follow-Ups

| Issue | Decision | Why |
|---|---|---|
| [#36](https://git.pdurlej.com/pdurlej/fallow-py/issues/36) | Fix | `--changed-only` outside Git can produce confusing feedback by combining a deprecation warning with a non-Git fallback warning. |
| [#37](https://git.pdurlej.com/pdurlej/fallow-py/issues/37) | Fix | TOML values with the wrong type should fail early with a field-specific `ConfigError` instead of leaking malformed values into analysis. |
| [#38](https://git.pdurlej.com/pdurlej/fallow-py/issues/38) | Fix | Source-root ordering should be an explicit specificity policy, not an accidental string-length heuristic. |
| [#39](https://git.pdurlej.com/pdurlej/fallow-py/issues/39) | Fix | Future agents need this curated triage note so the same audit does not get re-litigated after context compaction. |

## Deferred Or Research

| Issue | Decision | Why |
|---|---|---|
| [#40](https://git.pdurlej.com/pdurlej/fallow-py/issues/40) | Defer | MCP cache invalidation should be hardened, but it should be coordinated with cache lifecycle work in [#9](https://git.pdurlej.com/pdurlej/fallow-py/issues/9). |
| [#41](https://git.pdurlej.com/pdurlej/fallow-py/issues/41) | Research first | Parallel AST indexing may help, but fallow-py should benchmark real bottlenecks before adding concurrency. |
| [#11](https://git.pdurlej.com/pdurlej/fallow-py/issues/11) | Existing issue | Cycle-path/fingerprint stability already has a Phase B issue. DeepSeek's nondeterminism framing was overstated, but the canonicalization concern is covered. |
| [#27](https://git.pdurlej.com/pdurlej/fallow-py/issues/27) | Existing deferred issue | ADR 0009 implementation stays gated by ADR 0008 unless the operator explicitly pulls it forward. |

## Rejected Findings

These items should not be recreated as issues unless a concrete reproduction appears:

- `DEFAULT_IMPORT_MAP` missing `django`, `fastapi`, or `pydantic` as a direct bug. Those
  import names already match their distribution names; the map is mainly for mismatches
  such as `yaml` -> `pyyaml`.
- `_normalize_package_name` treating `_`, `-`, and `.` equivalently. That is expected
  package-name normalization behavior.
- `ExportRecord` tuples containing `None` being non-hashable. `None` is hashable.
- `.pyi` stubs as a near-term requirement. fallow-py uses inline typing and is pre-stable.
- `_dedupe_fragments()` dropping non-overlapping same-file duplicates. Current code reading
  does not support that claim; it needs a reproduction before tracking.

## Default Execution Order

When executing this triage batch, use:

1. This document.
2. `#36` changed-only non-Git UX.
3. `#37` strict config type validation.
4. `#38` explicit source-root ordering.
5. Leave `#40`, `#41`, and `#27` open unless the operator explicitly expands scope.
