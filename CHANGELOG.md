# Changelog

All notable changes to this project will be documented in this file.

This project follows the spirit of [Keep a Changelog](https://keepachangelog.com/) and uses semantic versioning while the public contract stabilizes.

## 0.3.0-alpha.1 - TBD

### Added

- `--format agent-fix-plan` for agent-native cleanup plans grouped as `auto_safe`, `review_needed`, `blocking`, and `manual_only`.
- `schemas/pyfallow-fix-plan.schema.json` for the fix-plan contract.
- Deterministic rule classification, investigation hints, and fix options for every pyfallow rule.
- Pre-edit `verify_imports` prediction through the MCP package and core `pyfallow.verify_imports` API.

### Changed

- Report schema version is now `1.2`.
- Core package version is now `0.3.0-alpha.1`.

## 0.2.0-alpha.1 - TBD

### Added

- Diff-aware analysis with `--since <git-ref>`.
- `analysis.diff_scope` in JSON reports.
- Separate `pyfallow-mcp` package with five MCP tools, two resource templates, and two prompts.
- Claude Code `pyfallow-cleanup` skill example and Cursor rule mirror for agent workflows.
- Public agent integration guide and small release zip assets for the bundled skill/rules.

### Changed

- `--changed-only` is now a deprecated alias for `--since HEAD~1` instead of a full-analysis fallback.
- Report schema version is now `1.1`.
- Core package version is now `0.2.0-alpha.1`; MCP package version starts at `0.1.0-alpha.1`.

## 0.1.0-alpha.1 - 2026-05-02

### Added

- Standalone `pyfallow` Python package and CLI.
- `fallow` compatibility console entry point for local workflows and future integration experiments.
- Python source discovery, module resolution, AST indexing, import graph, cycles, dead-code candidates, dependency findings, duplicate detection, complexity metrics, boundary rules, suppressions, baselines, SARIF, and agent-context output.
- JSON report schema and SARIF subset schema.
- Fixture projects, golden tests, and CLI smoke coverage.
- Release docs, examples, GitHub Actions CI, and community health files.

### Changed

- Version set to `0.1.0-alpha.1` to reflect early public API status.
- Project metadata hardened for editable installs, source distributions, and wheels.
- README rewritten for public release positioning and non-affiliation clarity.

### Fixed

- Parse-error modules no longer emit downstream dead-code, duplicate, or complexity findings.
- SyntaxError line/column data is preserved in parse-error issues.
- Test-scope references no longer mark production symbols as used when `include_tests=false`.
- Low-confidence star exports lower unused-symbol confidence instead of fully suppressing findings.
- SARIF fingerprints include source-line hashes when files are available.

### Known Limitations

- Python dynamic behavior means findings are advisory, not runtime proof.
- Dynamic imports, monkey patching, plugin loading, reflection, dependency injection containers, runtime path mutation, and framework magic can hide real usage.
