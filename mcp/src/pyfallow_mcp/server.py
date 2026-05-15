"""Compatibility shim for the legacy ``pyfallow_mcp.server`` entry point."""

from __future__ import annotations

import sys

from fallow_py_mcp.server import main as _canonical_main


def main(argv: list[str] | None = None) -> int:
    print(
        "`pyfallow-mcp` is deprecated; use `fallow-py-mcp` or `python -m fallow_py_mcp` instead.",
        file=sys.stderr,
    )
    return _canonical_main(argv, prog="pyfallow-mcp")

__all__ = ["main"]
