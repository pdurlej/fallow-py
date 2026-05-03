# fastapi-route

Tests decorator-based route registration.

Expected behavior: `list_items` must not be reported as an unused symbol.

Why this is tough: FastAPI consumes route handlers through decorators; no ordinary Python caller may
reference the function.

How pyfallow handles it: route decorators mark the function as framework-managed.
