# Schema

The canonical report format is JSON. It is designed for agents, reviewers, CI, and future Fallow integration.

Schema files live in [`../schemas`](../schemas):

- `pyfallow-report.schema.json`
- `pyfallow-sarif.schema.json`

## Top-Level Report

Required top-level fields:

- `tool`
- `language`
- `version`
- `schema_version`
- `root`
- `config_path`
- `generated_at`
- `analysis`
- `summary`
- `issues`
- `metrics`
- `graphs`
- `config`
- `limitations`

`generated_at` is currently `null` to keep tests and baseline output deterministic.

## Analysis Metadata

`analysis.changed_only` is retained for compatibility with v0.1 consumers. In schema `1.1`, diff-aware runs also include `analysis.diff_scope`:

- `since`: requested Git ref, or `null`
- `since_resolved`: resolved commit SHA when Git resolution succeeds
- `changed_files`: changed Python files after ignore filtering
- `changed_modules`: discovered modules corresponding to changed files
- `filtering_active`: whether issue filtering was applied
- `reason`: human-readable explanation or fallback warning

`--changed-only` is a deprecated alias for `--since HEAD~1`. Consumers should prefer `diff_scope` for new integrations.

## Issue Core

Each issue includes:

- `id`: stable `PYxxx` rule id
- `rule`: slug such as `unused-symbol`
- `category`: broad analyzer category
- `severity`: `info`, `warning`, or `error`
- `confidence`: `low`, `medium`, or `high`
- `path`, `range`, `symbol`, and `module`
- `message`
- `evidence`
- `actions`
- `fingerprint`

`evidence` and `actions` are intentionally extensible. Consumers should tolerate added keys.

## Severity And Confidence

Severity describes expected workflow impact. Confidence describes static-analysis certainty.

Python is dynamic, so confidence matters:

- `high`: strong static evidence, still not runtime proof
- `medium`: likely useful, review before acting
- `low`: signal for inspection or uncertainty tracking

Low-confidence dead-code findings should not be auto-deleted.

## Graphs

`graphs.modules` exposes module nodes, state, exports, and symbol state. Symbol state includes separate production, test, and type-only reference counts.

`graphs.edges` exposes local import edges.

`graphs.cycles` exposes cycle paths and supporting import lines.

`graphs.duplicate_groups` exposes duplicate fragments.

`graphs.exports` exposes first-class export records.

## SARIF Notes

SARIF output targets SARIF 2.1.0 compatibility:

- rule ids are `PYxxx`
- descriptor names use pyfallow rule slugs
- result level maps from pyfallow severity
- result properties include confidence
- fingerprints include `pyfallowFingerprint` and `primaryLocationLineHash`
- cycles and duplicates include capped related locations

## Schema Versioning Policy

`schema_version` follows compatibility semantics:

- `1.1` adds optional `analysis.diff_scope` for diff-aware analysis
- additive fields are allowed within the same major schema version
- removals and renames require a major schema version bump
- `evidence` and `actions` remain extensible
- consumers should ignore unknown fields unless they opt into strict validation

Tests include an internal validator for required contract keys. Full JSON Schema validation can be added as a dev-only dependency later if it adds value without becoming a runtime dependency.
