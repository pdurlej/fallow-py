# Performance and Complementary Stack Benchmarks

pyfallow is designed to run alongside existing Python quality tools. This page documents a reproducible local benchmark for `ruff`, `vulture`, `deptry`, and `pyfallow`; it is not a ranking.

## Methodology

Harness:

```bash
python benchmarks/comparison/run.py --repo all --tool all --runs 5 --execute
```

Repository set:

- `requests` at `8f6cda9969f4a98c45ea2922f6bcbefc02256202`
- `fastapi` at `e0a2c75b1a980c52c336cfefd12f2277238c4e8f`
- `flask` at `7374c85ddefc3f4b177a698ab9f0cbb6a5c0b392`
- `pydantic` at `597fa692eaaa90132f683e88ca994f28e185463b`
- `httpx` at `b5addb64f0161ff6bfe94c124ef76f6a1fba5254`

Tool versions:

- `ruff 0.15.12`
- `vulture 2.16`
- `deptry 0.25.1`
- `pyfallow 0.3.0-alpha.1`

Local benchmark environment:

- Apple M1 Max
- macOS 26.4.1 arm64
- Python 3.14.4
- Five timed runs per repository/tool pair
- Common tool caches such as `.ruff_cache` are removed before each timed run
- Project runtime dependencies for the cloned repositories are not installed

The dependency choice matters: `deptry` and pyfallow can report missing imports that would look different if every optional/test dependency were installed or configured. Treat these numbers as reproducible calibration data, not universal truth.

## Median Runtime

Median seconds across five clean-cache runs:

| Repo | ruff | vulture | deptry | pyfallow |
| --- | ---: | ---: | ---: | ---: |
| requests | 0.021s | 0.179s | 0.121s | 0.245s |
| fastapi | 0.082s | 1.076s | 0.276s | 1.437s |
| flask | 0.024s | 0.259s | 0.142s | 0.235s |
| pydantic | 0.047s | 2.490s | 0.268s | 2.650s |
| httpx | 0.024s | 0.337s | 0.188s | 0.394s |

Interpretation: `ruff` is much faster for its per-file linting job. pyfallow is in the same order of magnitude as repo-wide dead-code tooling on these projects, but speed is not the core claim; the core claim is repo-wide, agent-readable structural context.

## Finding Counts

Counts are not a score. More findings does not mean better analysis; each tool answers a different question.

| Repo | ruff | vulture | deptry | pyfallow |
| --- | ---: | ---: | ---: | ---: |
| requests | 0 | 89 | 76 | 121 |
| fastapi | 0 | 1523 | 934 | 843 |
| flask | 0 | 342 | 268 | 107 |
| pydantic | 0 | 1501 | 571 | 678 |
| httpx | 0 | 63 | 43 | 74 |

Ruff reported zero issues here because these mature projects are already clean under the invoked `ruff check` configuration. That is an expected strength of ruff in maintained repositories, not a weakness.

## Coverage by Aspect

Aggregated findings by broad aspect:

| Aspect | ruff | vulture | deptry | pyfallow |
| --- | ---: | ---: | ---: | ---: |
| Style/per-file lint | 0 | 0 | 0 | 0 |
| Dead code | 0 | 3518 | 0 | 839 |
| Dependencies | 0 | 0 | 1892 | 84 |
| Import cycles | 0 | 0 | 0 | 0 |
| Boundaries | 0 | 0 | 0 | 0 |

The selected public repositories do not include pyfallow boundary rules, so boundary counts are not applicable. Cycle counts are zero in this run; cycle detection is still part of pyfallow's value on applications that have cycles.

## Tool Fit

### ruff

**Best at:** style, formatting-adjacent lint, import sorting, and very fast per-file quality checks.

**Add pyfallow when:** you also want repo-wide import graph analysis, cycles, boundary rules, dependency scope context, and agent-native cleanup plans.

### vulture

**Best at:** battle-tested dead-code heuristics with a focused CLI.

**Add pyfallow when:** you want dead-code candidates connected to module reachability, framework uncertainty, confidence, and machine-readable actions.

### deptry

**Best at:** dependency declaration versus observed imports.

**Add pyfallow when:** you also want dependency scope policy, type-only/test-only lowering, pre-edit hallucinated import checks, and graph findings in the same report.

### pyfallow

**Best at:** repo-wide graph, architecture boundaries, confidence-carrying cleanup findings, duplicate/complexity overlap, and agent-native JSON/MCP loops.

**Use alongside:** ruff for per-file quality, mypy or pyright for types, vulture for another dead-code opinion, deptry for focused dependency policy, and CodeQL/Semgrep for security.

## Reproduce

```bash
python benchmarks/comparison/run.py --list
python benchmarks/comparison/run.py --repo requests --tool pyfallow --dry-run
python benchmarks/comparison/run.py --repo all --tool all --runs 5 --execute
```

Generated results are written under `benchmarks/comparison/results/` and intentionally ignored. Commit updated numbers only after recording the machine, Python version, tool versions, and run command.
