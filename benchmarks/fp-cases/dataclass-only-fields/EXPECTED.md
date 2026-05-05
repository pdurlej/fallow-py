# dataclass-only-fields

Tests dataclass model declarations.

Expected behavior: `Item` must not be reported as unused.

Why this is tough: data models are often consumed by serialization, validation, tests, or external APIs
through shape rather than direct calls.

How pyfallow handles it: dataclass decorators mark the class as framework/model managed.
