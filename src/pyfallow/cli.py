"""Compatibility shim for the legacy ``pyfallow.cli`` entry point."""

from __future__ import annotations

import sys

from fallow_py.cli import main as _canonical_main


def main(argv: list[str] | None = None) -> int:
    print(
        "`pyfallow` is deprecated; use `fallow-py` or `python -m fallow_py` instead.",
        file=sys.stderr,
    )
    return _canonical_main(argv, prog="pyfallow")

__all__ = ["main"]
