"""Compatibility entry point for ``python -m pyfallow_mcp``."""

from __future__ import annotations

from fallow_py_mcp.server import main


if __name__ == "__main__":
    raise SystemExit(main())
