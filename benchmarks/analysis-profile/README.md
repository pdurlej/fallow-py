# Pyfallow Analysis Profile Benchmark

This harness profiles pyfallow's own analyzer phases before any implementation work on
parallel AST indexing. It is intentionally a measurement tool, not an optimization.

Run the configured case list:

```bash
python benchmarks/analysis-profile/run.py --list
```

Run a small checked-in project and a larger generated fixture:

```bash
python benchmarks/analysis-profile/run.py --case all --generated-modules 120 --runs 3
```

Generated fixtures are written under `benchmarks/analysis-profile/workspace/`.
Profile output is written to `benchmarks/analysis-profile/results/analysis-profile.json` unless
`--output` is provided.

## Cases

- `demo-project`: the checked-in example project with dependency, graph, duplicate, complexity,
  and boundary findings.
- `generated`: a deterministic pure-Python package sized with `--generated-modules`.

## Phases

The script temporarily wraps pyfallow's internal functions while it runs in the benchmark process.
It does not change production analyzer behavior.

Measured phases:

- source discovery
- file indexing
- module resolution
- dependency analysis
- graph analysis
- boundary analysis
- duplicate detection
- dead-code analysis
- complexity analysis
- suppression/fingerprinting
- JSON serialization

## Current Local Snapshot

Captured on 2026-05-12 with Python 3.14.4 on Apple M1 Max:

| Case | Files | Imports | Issues | Median total | Largest measured phases |
| --- | ---: | ---: | ---: | ---: | --- |
| `demo-project` | 12 | 12 | 17 | 0.007018s | source discovery 0.001413s; duplicate detection 0.001413s; file indexing 0.001281s |
| `generated --generated-modules 120` | 122 | 41 | 297 | 0.076249s | file indexing 0.021216s; complexity 0.014413s; source discovery 0.011337s |

## Decision

Do not implement parallel AST indexing yet. On the current small and generated fixtures, pyfallow is
already sub-100ms and the measured cost is spread across indexing, complexity, discovery,
duplicate detection, and module resolution. Parallel indexing may still become worthwhile on real
large repositories, but it needs a larger measured corpus before adding concurrency and preserving
determinism becomes worth the complexity.
