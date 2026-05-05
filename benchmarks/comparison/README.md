# Complementary Stack Benchmarks

This harness compares where `ruff`, `vulture`, `deptry`, and `pyfallow` fit in the same Python quality stack. It is not a winner-takes-all benchmark.

The pinned repository subset matches the first five entries in `benchmarks/soak/repos.toml`.

## Usage

Inspect the matrix:

```bash
python benchmarks/comparison/run.py --list
```

Write deterministic plans without cloning or installing tools:

```bash
python benchmarks/comparison/run.py --repo requests --tool pyfallow --dry-run
```

Run one pyfallow shakedown:

```bash
python benchmarks/comparison/run.py --repo requests --tool pyfallow --runs 1 --execute
```

Run the full 5-repo x 4-tool x 5-run matrix:

```bash
python benchmarks/comparison/run.py --repo all --tool all --runs 5 --execute
```

Generated repositories, virtual environments, and results are intentionally ignored:

- `benchmarks/comparison/workspace/`
- `benchmarks/comparison/venvs/`
- `benchmarks/comparison/results/`

Summarize and publish numbers only after recording hardware, Python version, tool versions, and whether repositories were analyzed with their own native dependencies installed.
