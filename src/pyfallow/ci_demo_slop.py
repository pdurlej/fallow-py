"""CI demo slop — intentional findings for live TICKET-I validation PR.

This file is added on `test/ticket-i-live-validation` branch ONLY, to verify
that .forgejo/workflows/ci.yml triggers correctly, runs pyfallow analyze on
the PR diff, and posts a classified comment on the PR.

Expected pyfallow findings (per `--format agent-fix-plan`):

- BLOCKING:
    * missing-runtime-dependency for `nonexistent_pkg_for_ci_demo`
      (the package does not exist on PyPI and is not declared in
      pyproject.toml)

- REVIEW NEEDED:
    * unused-module for `pyfallow.ci_demo_slop` (this module is not
      reachable from any configured entrypoint in `.pyfallow.toml`)
    * unused-symbol for `demo_unused_helper` (defined but unreferenced)

This module MUST NOT be merged to main. The PR should be closed without
merge once CI validation has been observed.
"""

from nonexistent_pkg_for_ci_demo import unknown_function  # type: ignore[import-not-found]


def demo_unused_helper() -> str:
    """Intentionally unused — exists only to surface unused-symbol classification."""
    return unknown_function()
