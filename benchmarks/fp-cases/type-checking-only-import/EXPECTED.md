# type-checking-only-import

Tests imports guarded by `typing.TYPE_CHECKING`.

Expected behavior: missing `pandas` is a low-confidence info-level type dependency finding, not a
blocking runtime dependency finding.

Why this is tough: the import appears in Python source but is intentionally not executed at runtime.

How pyfallow handles it: TYPE_CHECKING depth is tracked during AST indexing and dependency policy lowers
the finding scope.
