# optional-dependency-guard

Tests guarded optional imports.

Expected behavior: guarded `orjson` should not become a runtime dependency violation.

Why this is tough: optional imports are real runtime imports, but the fallback path intentionally handles
missing packages.

How fallow-py handles it: imports inside `try` blocks guarded by `ImportError` or `ModuleNotFoundError`
are classified as optional guarded imports.
