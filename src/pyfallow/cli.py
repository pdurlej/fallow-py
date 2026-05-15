"""Compatibility shim for the legacy ``pyfallow.cli`` entry point."""

from __future__ import annotations

from fallow_py.cli import main

__all__ = ["main"]
