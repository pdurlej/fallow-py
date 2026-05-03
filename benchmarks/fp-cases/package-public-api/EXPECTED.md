# package-public-api

Tests package-level public API exports.

Expected behavior: `foo` is public API through `lib.__all__` and must not be reported as unused.

Why this is tough: public APIs may be consumed by downstream users outside the repository, so local
reachability is not the same as usage.

How pyfallow handles it: explicit `__all__` reexports propagate public API state to the origin symbol.
