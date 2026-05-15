# Contributing

Thanks for helping improve fallow-py.

The most valuable contributions right now are correctness fixes, false-positive reductions, fixture projects, documentation, and release engineering. Please avoid expanding analyzer categories unless there is an accepted design discussion first.

## Development Setup

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src tests
python -m pytest -q
```

Runtime code must remain stdlib-only. Dev and packaging tools belong in the `dev` extra.

## CLI Smoke Tests

Run these before opening a PR:

```bash
python -m fallow_py --help
python -m fallow_py --format json --root . --output /tmp/pyfallow-report.json
python -m fallow_py analyze --format text --root .
python -m fallow_py analyze --format sarif --root . --output /tmp/pyfallow.sarif
python -m fallow_py agent-context --format markdown --root . --output /tmp/pyfallow-agent-context.md
python -m fallow_py baseline create --root . --output /tmp/pyfallow-baseline.json
python -m fallow_py baseline compare --root . --baseline /tmp/pyfallow-baseline.json
```

## Coding Principles

- Never execute analyzed project code.
- Never import analyzed project modules dynamically.
- Keep runtime dependencies at zero outside the standard library.
- Keep output deterministic.
- Preserve confidence and evidence instead of overclaiming precision.
- Prefer narrow fixes over broad refactors.
- Keep tests focused on behavior and false-positive prevention.

## Fixtures And Golden Outputs

Add fixture projects when changing behavior that affects graph, dependency, dead-code, duplicate, complexity, SARIF, baseline, or schema output.

When golden output changes:

1. Confirm the behavior change is intentional.
2. Update the golden file.
3. Mention the contract impact in the PR.
4. Update schema/docs when the public shape changes.

## Reporting False Positives

False-positive reports should include:

- rule id and rule slug
- finding excerpt
- minimal code pattern
- framework or library involved
- why the code is actually used
- expected severity or confidence

## PR Checklist

- Tests added or updated.
- Golden outputs updated when output changed.
- No runtime dependencies added unless explicitly justified.
- Analyzed project code is never executed.
- Docs updated for user-visible behavior.
- CLI smoke commands run.
- Schema compatibility considered.
- README examples still work.

