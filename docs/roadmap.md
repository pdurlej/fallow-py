# Roadmap

No dates are promised. The priority is trustworthiness before feature breadth.

## Now

- Keep runtime stdlib-only.
- Preserve deterministic JSON output.
- Keep tests and golden outputs stable.
- Improve documentation, examples, packaging, and release hygiene.
- Collect false positives from real projects.

## Next

- Tighten scope correctness for tests, type-only imports, and optional dependencies.
- Improve import/export resolution for complex package APIs.
- Expand schema validation and compatibility tests.
- Strengthen SARIF validation against common consumers.
- Implement real `--changed-only` using git diff when available, with graceful fallback.

## Later

- Optional adapters for installed tools such as Ruff, Vulture, Deptry, Radon, Pyright, or Mypy.
- Package-level coupling and instability summaries.
- Editor/problem-matcher output.
- More framework-specific confidence reducers.
- Native bridge into an upstream Fallow CLI if the project is formally integrated.

## Non-Goals

- Executing analyzed project code.
- Runtime network calls.
- Replacing type checkers or linters.
- Claiming perfect dead-code proof for dynamic Python.
- Auto-deleting code.
- PyPI auto-publish before package ownership and metadata are confirmed.

