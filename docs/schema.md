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

- additive fields are allowed within the same major schema version
- removals and renames require a major schema version bump
- `evidence` and `actions` remain extensible
- consumers should ignore unknown fields unless they opt into strict validation

Tests include an internal validator for required contract keys. Full JSON Schema validation can be added as a dev-only dependency later if it adds value without becoming a runtime dependency.

