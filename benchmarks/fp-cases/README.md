# False-Positive Case Corpus

This corpus contains small Python projects that exercise known false-positive surfaces for static
analysis. Each case includes:

- `pyproject.toml` and minimal source files
- `expected.json` used by tests
- `EXPECTED.md` explaining why the case is difficult and what pyfallow should do

The corpus is intentionally small. If a project finds a new false positive, add the smallest
reproduction here before changing analyzer behavior.

| Case | Surface | Expected behavior |
| --- | --- | --- |
| `django-management-command` | Django command discovery | Command module and command entry symbols are not reported as dead code. |
| `fastapi-route` | Decorator route registration | Route handler is framework-managed, not unused. |
| `package-public-api` | `__init__.py` reexport and `__all__` | Public API export suppresses unused-symbol for the origin. |
| `optional-dependency-guard` | Optional import guard | Guarded optional import is not a runtime dependency violation. |
| `type-checking-only-import` | `TYPE_CHECKING` import | Missing type dependency stays low/info, not runtime blocking. |
| `namespace-package-ambiguity` | Multiple roots mapping same module | Ambiguity is reported; related dead-code signal remains low confidence. |
| `protocol-class` | Structural typing surface | Protocol class is not treated as unused implementation code. |
| `dataclass-only-fields` | Data model consumed by shape | Dataclass model is not treated as an unused symbol. |
| `celery-shared-task` | Task decorator registration | Shared task function is framework-managed; module uncertainty stays low. |
