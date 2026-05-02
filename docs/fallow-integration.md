# Future Fallow Integration

`pyfallow` is inspired by `fallow-rs/fallow`, but it is not currently an official fallow-rs/fallow project and does not imply endorsement or affiliation.

The current repository is a standalone Python package and CLI. This was the safest integration path because the repository started empty and had no existing Rust, Node, or shared Fallow core to extend.

## Compatibility Surface

The package installs two console scripts:

- `pyfallow`
- `fallow`

The `fallow` entry point is a compatibility bridge for local workflows and possible future integration. It accepts patterns such as:

```bash
fallow --format json --root .
fallow analyze --language python --format json --root .
fallow python --format json --root .
fallow python agent-context --format markdown --root .
```

## Subprocess Backend Contract

A future upstream Fallow CLI could invoke pyfallow as a subprocess:

```bash
python -m pyfallow analyze --language python --format json --root <repo>
```

Expected output:

- stdout contains the requested report format unless `--output` is used
- stderr contains tool/runtime errors
- exit codes follow pyfallow CLI semantics
- JSON report uses `schema_version`

## Input Contract

Minimum inputs:

- analysis root
- config path or discoverable config
- output format
- optional baseline path
- thresholds such as `--fail-on`, `--min-confidence`, and `--severity-threshold`

The backend must not require network access and must not execute analyzed project code.

## Output Contract

The JSON report is the integration contract. Consumers should read:

- `summary`
- `issues`
- `graphs`
- `metrics`
- `analysis.entrypoints`
- `analysis.frameworks_detected`
- `limitations`

Issue `fingerprint` is intended for baselines and regression gating.

## What Real Upstream Integration Would Need

- agreement on ownership and naming
- schema compatibility review
- a stable language-backend invocation protocol
- end-to-end tests from the upstream CLI
- documentation that distinguishes official integration from this standalone package
- release process alignment

Until that happens, pyfallow should describe itself as inspired by Fallow, not official Fallow.

