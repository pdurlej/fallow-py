"""Compatibility shim for the renamed :mod:`fallow_py_mcp` package."""

from __future__ import annotations

import importlib
import sys
import warnings

warnings.warn(
    "`pyfallow_mcp` package name is deprecated; import from `fallow_py_mcp` instead. "
    "The shim will be removed in 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)

_IMPL = importlib.import_module("fallow_py_mcp")

_SUBMODULES = (
    "advice",
    "context",
    "remediation",
    "runtime",
    "safety",
    "schemas",
    "tools",
)

for _name in _SUBMODULES:
    _module = importlib.import_module(f"fallow_py_mcp.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

for _name in getattr(_IMPL, "__all__", ()):
    globals()[_name] = getattr(_IMPL, _name)

__all__ = list(getattr(_IMPL, "__all__", ()))
__version__ = getattr(_IMPL, "__version__")
