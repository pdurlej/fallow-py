# pyfallow

[![CI](https://github.com/pd/fallow-python/actions/workflows/ci.yml/badge.svg)](https://github.com/pd/fallow-python/actions/workflows/ci.yml)

`pyfallow` is an early Python-first codebase intelligence tool for agents and reviewers.

It builds a static picture of imports, dependencies, complexity, duplication, architecture boundaries, and likely dead code without importing or executing the project under analysis. Python is dynamic, so findings carry confidence, evidence, and suggested actions instead of pretending to be runtime truth.

## Status

Current release target: `0.1.0-alpha.1`.

Runtime dependencies are stdlib-only on Python 3.11+. Development and packaging tools are optional extras.

## Why pyfallow?

- Built for code agents and human reviewers.
- Project-wide graph analysis, not file-local linting.
- Deterministic JSON for automation.
- SARIF 2.1.0 for code scanning consumers.
- Baselines for CI adoption with existing debt.
- Conservative Python static analysis with confidence and evidence.

## What It Checks

`pyfallow` currently reports:

- Python source discovery and module resolution
- local import graph edges and circular dependencies
- likely unused modules and top-level symbols
- declared-but-unused runtime dependencies
- missing runtime, test-only, type-only, dev-only, and optional dependency scope issues
- duplicate code blocks using normalized token windows
- cyclomatic and cognitive complexity hotspots
- configured architecture boundary violations
- parse/config errors
- stale suppressions

It also emits graph data, baseline comparisons, SARIF, and compact agent-context reports.

## Quickstart

From a fresh clone:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pyfallow analyze --root examples/demo_project --format text
```

Without installing:

```bash
PYTHONPATH=src python -m pyfallow analyze --root examples/demo_project --format text
```

Generate machine-readable output:

```bash
python -m pyfallow analyze --root examples/demo_project --format json --output /tmp/pyfallow-report.json
python -m pyfallow analyze --root examples/demo_project --format sarif --output /tmp/pyfallow.sarif
python -m pyfallow agent-context --root examples/demo_project --format markdown --output /tmp/pyfallow-agent-context.md
```

Installed console scripts:

```bash
pyfallow --format json --root .
fallow --format json --root .
fallow analyze --language python --format json --root .
fallow python --format json --root .
```

The `fallow` command is a compatibility bridge for local workflows and possible future integration. It does not mean this project is official Fallow.

## 30-Second Demo

Run the bundled demo project:

```bash
python -m pyfallow analyze --root examples/demo_project --format text
```

Example text output excerpt:

```text
PY040 error high examples/demo_project/src/app/main.py:3 Imported third-party package 'missingdep' is not declared as a dependency.
PY020 warning high examples/demo_project/src/app/cycle_a.py:1 Import cycle detected: app.cycle_a -> app.cycle_b -> app.cycle_a
PY070 error high examples/demo_project/src/app/domain/service.py:1 Import violates architecture boundary rule 'domain-no-infra'.
```

Short checked-in excerpts live in [`examples/outputs/`](examples/outputs/).

## Agent Workflow

Use `agent-context` before broad edits:

```bash
python -m pyfallow agent-context --root . --format markdown --output /tmp/pyfallow-agent-context.md
```

Recommended workflow:

1. Inspect parse errors and config errors first.
2. Inspect missing runtime dependencies, boundary violations, and cycles before refactors.
3. Review hotspots before changing shared modules.
4. Treat high-confidence dead modules as candidates, not deletion instructions.
5. Do not auto-delete low-confidence or framework-adjacent dead code.
6. Rerun pyfallow after edits and compare new/resolved findings.

## CI Workflow

Create a baseline for existing debt:

```bash
python -m pyfallow baseline create --root . --output .fallow-baseline.json
```

Gate on new findings:

```bash
python -m pyfallow analyze --root . \
  --baseline .fallow-baseline.json \
  --fail-on warning \
  --min-confidence medium
```

Exit codes:

- `0`: no blocking issues under the active thresholds
- `1`: blocking issues found under `--fail-on`
- `2`: tool, config, or runtime error
- `3`: parse errors severe enough to invalidate analysis

The included GitHub Actions workflow uses pyfallow self-analysis as smoke only; it does not fail CI on pyfallow findings from this repository.

## Configuration

Supported config files:

- `.fallow.toml`
- `.pyfallow.toml`
- `pyproject.toml` under `[tool.fallow.python]` or `[tool.pyfallow]`

Minimal example:

```toml
[tool.pyfallow]
roots = ["src"]
entry = ["src/app/main.py"]
include_tests = false

[tool.pyfallow.dupes]
min_lines = 6
min_tokens = 40

[tool.pyfallow.health]
max_cyclomatic = 10
max_cognitive = 15

[[tool.pyfallow.boundaries.rules]]
name = "domain-no-infra"
from = "src/app/domain/**"
disallow = ["src/app/infra/**"]
severity = "error"
```

See [`examples/demo_project/.pyfallow.toml`](examples/demo_project/.pyfallow.toml) for a compact working configuration.

## Suppressions

Supported prefixes:

```python
# fallow: ignore
# fallow: ignore[unused-symbol]
# fallow: ignore[unused-module]
# fallow: ignore[missing-runtime-dependency]
# fallow: ignore[unused-runtime-dependency]
# fallow: ignore[missing-dependency]  # legacy alias for split dependency rules
# fallow: ignore[unused-dependency]   # legacy alias for split dependency rules
# fallow: ignore[duplicate-code]
# fallow: ignore[high-complexity]
# fallow: expected-unused

# pyfallow: ignore[unused-symbol]
```

Suppressions apply to the same line, symbol definition lines, or the whole file when placed near the top of the file. Stale suppressions are reported when practical.

## Output Formats

- `text`: compact human-readable diagnostics
- `json`: deterministic machine-readable report
- `sarif`: SARIF 2.1.0 for code scanning consumers
- `markdown`: used by `agent-context`
- `mermaid` and `dot`: graph command output

JSON reports include summary, issues, metrics, graph data, config metadata, and limitations. `evidence` and `actions` are intentionally extensible.

## Baseline Usage

```bash
python -m pyfallow baseline create --root . --output .fallow-baseline.json
python -m pyfallow baseline compare --root . --baseline .fallow-baseline.json --format json
python -m pyfallow analyze --root . --baseline .fallow-baseline.json --fail-on warning --min-confidence medium
```

When a baseline is active, CI failure considers only new findings.

## GitHub Code Scanning / SARIF

Generate SARIF:

```bash
python -m pyfallow analyze --root . --format sarif --output pyfallow.sarif
```

SARIF includes rule metadata, levels mapped from pyfallow severity, result confidence, stable fingerprints, source-line hashes where files are available, and capped related locations for cycles and duplicate groups.

The default CI workflow does not upload SARIF. Enable code scanning intentionally after repository permissions and retention expectations are clear.

## Examples Directory

- [`examples/demo_project/`](examples/demo_project/) contains a small project with missing dependencies, an unused dependency, a cycle, a duplicate, a complexity hotspot, a boundary violation, suppressions, and public API reexports.
- [`examples/outputs/`](examples/outputs/) contains short output excerpts for README and release notes.

## Limitations

Static Python analysis is approximate. Known limits include dynamic imports, monkey patching, reflection, dependency injection containers, framework magic, plugin entry points, namespace package ambiguity, generated code, runtime path mutation, conditional imports, and public API that may be consumed outside the repository.

See [`docs/limitations.md`](docs/limitations.md) for details.

## Relationship To fallow-rs/fallow

`pyfallow` is inspired by [`fallow-rs/fallow`](https://github.com/fallow-rs/fallow), but it is not currently an official fallow-rs/fallow project and does not imply endorsement or affiliation.

This repository follows the standalone integration path: a Python package and CLI with stable JSON/SARIF output that could later be called by a broader Fallow CLI. The installed `fallow` console entry point is a compatibility bridge for future integration and local workflows.

See [`docs/fallow-integration.md`](docs/fallow-integration.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src tests
python -m pytest -q
python -m pyfallow analyze --root examples/demo_project --format json
python -m build
python -m twine check dist/*
```

Runtime code must remain stdlib-only and must never execute analyzed project code.

## Contributing

Contributions are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), especially the guidance on false positives, fixtures, golden outputs, and the no-runtime-execution safety rule.

## License

MIT. See [`LICENSE`](LICENSE).
