"""Compatibility shim for the legacy ``pyfallow_mcp.server`` entry point."""

from __future__ import annotations

from fallow_py_mcp.server import main

__all__ = ["main"]
