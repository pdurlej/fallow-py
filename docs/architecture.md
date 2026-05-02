# Architecture

`pyfallow` is a standalone Python static analysis backend. The runtime intentionally uses only the Python standard library so it can run in clean agent, CI, and review environments without bringing extra analyzer dependencies.

## Pipeline

The high-level pipeline is:

1. Load configuration from `.fallow.toml`, `.pyfallow.toml`, or `pyproject.toml`.
2. Discover source roots and Python files.
3. Resolve file paths to Python module names.
4. Parse files with `ast` and index imports, symbols, references, exports, suppressions, and framework hints.
5. Resolve local imports and classify imports as local, stdlib, third-party, dynamic, or unresolved.
6. Build a local import graph.
7. Run analyzers over indexed artifacts.
8. Apply suppressions and assign stable fingerprints.
9. Format JSON, text, SARIF, graph, baseline, or agent-context output.

## Source Discovery

Discovery starts from configured roots when provided. Otherwise it looks for common source directories such as `src`, `app`, `backend`, `server`, and `service`, plus root-level packages and scripts. Output paths are normalized to POSIX separators relative to the analysis root.

Ignored paths include virtual environments, caches, build directories, package metadata, and common generated folders.

## AST Indexing

Indexing is static and non-executing. `pyfallow` parses Python files with `ast.parse` and never imports analyzed project modules. Parse failures become `parse-error` issues and downstream analyzers skip those modules.

The index captures:

- imports and dynamic import calls
- top-level functions, classes, assignments, and annotated assignments
- function metadata for complexity analysis
- direct name references and visible attribute references
- `__all__` exports and package reexports
- suppressions
- conservative framework hints

Raw AST nodes are kept inside internal function/index structures for complexity analysis, not in public report objects.

## Module Resolution

The resolver maps paths to module names using source-root-relative paths:

- `src/pkg/foo.py` becomes `pkg.foo`
- `src/pkg/__init__.py` becomes `pkg`
- `manage.py` becomes `manage`

Relative imports are resolved against the importer package. The resolver tries both submodule and symbol interpretations for `from package import name`.

If multiple configured source roots map files to the same module, the first deterministic path is used and ambiguity evidence is exposed in `analysis.module_ambiguities`.

## Import Graph

The graph is module-to-module:

- node: Python module
- edge: local import dependency

Edges include path, line, imported symbol, import kind, confidence, type-checking marker, and dynamic marker. Test edges are excluded from production graph behavior when `include_tests=false`, but production imports of test modules are still reported.

Cycles are detected with strongly connected components and reported with import-line evidence.

## Analyzer Modules

Analyzer modules are intentionally small:

- `dead_code`: reachability, unused modules, unused symbols, public API confidence, test/reference scope separation
- `dependencies`: declared dependency parsing and import policy checks
- `dupes`: normalized token-window duplicate detection
- `complexity`: cyclomatic complexity, cognitive approximation, size, and hotspot scoring
- `boundaries`: configured architecture boundary rules
- `suppressions`: inline suppression matching and stale suppression reporting
- `baseline`: fingerprint-based create/compare helpers
- `sarif` and `formatters`: output conversion

## AnalysisContext

`AnalysisContext` is the boundary object passed after indexing and graph construction. It groups configuration, source roots, modules, graph, dependency declarations, entrypoints, and entrypoint symbols. It is an artifact boundary, not a claim of deep immutability; it contains mutable module objects populated during analysis.

## Output Formatting

JSON is the canonical output. Text, SARIF, graph, baseline, and agent-context output are derived from the same result model.

Stable ordering is preferred throughout the pipeline so reports are suitable for CI, baselines, and agent context.

## Future Integration Points

Optional external adapters could be added later behind explicit configuration. Good candidates include Ruff, Vulture, Deptry, Radon, Pyright, and Mypy. They should remain optional and must not replace the stdlib-only core.

An upstream Fallow integration could call `pyfallow` as a subprocess language backend and consume the JSON report contract.

