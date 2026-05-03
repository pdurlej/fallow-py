# Limitations

`pyfallow` is a static and semi-static analyzer. It never imports or executes analyzed project code. That safety choice means findings are approximate.

## Dynamic Imports

String-literal calls such as `importlib.import_module("pkg.mod")` can be resolved when the target exists. Non-literal dynamic imports are tracked as uncertainty.

## Monkey Patching

Runtime assignment to modules, classes, functions, or imports is not modeled.

## Reflection

`getattr`, `setattr`, `globals`, `locals`, descriptor tricks, and metaclass behavior can hide real usage from static analysis.

## Dependency Injection

Dependency injection containers and service locators may reference classes by strings, annotations, config, or runtime registration. pyfallow does not fully model those systems.

## Framework Magic

Framework heuristics lower false positives for common Django, FastAPI, Flask, Celery, pytest, Click, Typer, SQLAlchemy, Pydantic, and dataclass patterns. They do not prove runtime reachability.

## Plugin Entry Points

Package entry points and plugin systems may expose code that is not imported by local source files. Configure explicit entries or suppress low-confidence findings when needed.

## Namespace Package Ambiguity

Namespace packages are supported, but unusual source-root layouts can map multiple files to the same module name. Ambiguities are reported in analysis metadata where detected.

## Generated Code

Generated files are skipped only when markers or common generated paths are obvious. Projects with generated source should add ignore patterns.

## Runtime Path Mutation

Changes to `sys.path`, `PYTHONPATH`, import hooks, and loader behavior are not modeled.

## Conditional Imports

Imports guarded by environment checks, platform checks, optional dependency handling, or `try/except ImportError` are classified statically. Runtime environments may differ.

## Public API vs Actual Usage

Public exports are not the same as runtime usage. High- and medium-confidence public API evidence suppresses some unused-symbol findings by default. Low-confidence public API evidence lowers confidence or marks uncertainty instead of fully suppressing.

## Known False-Positive Surfaces

The soak harness in `benchmarks/soak/` exists to calibrate these surfaces on real projects. Current expected risk areas:

- `unused-module`: plugin registries, Django app discovery, Celery task autodiscovery, and dynamically imported command modules.
- `unused-symbol`: public APIs, decorators that register callbacks, framework hooks, and symbols referenced from templates or config files.
- `missing-runtime-dependency`: vendored packages, monorepo-local packages not under configured roots, and import-to-distribution names that need explicit mapping.
- `unused-runtime-dependency`: plugin packages, package metadata dependencies, optional extras, and runtime imports hidden behind reflection.
- `circular-dependency`: type-only imports and import cycles already mitigated by local import placement.
- `duplicate-code`: repeated structural shape that represents different domain concepts.
- `high-complexity`: parser/compiler-style code and explicit state machines where branching is intentional.
- `boundary-violation`: rules that do not match the repository's actual architecture vocabulary.

If a rule shows more than a 30% false-positive rate during calibration, lower severity/confidence or document a targeted heuristic before presenting the rule as a CI blocker.

## Checked False-Positive Cases

The fixed corpus in [`benchmarks/fp-cases/`](../benchmarks/fp-cases/) turns common false-positive
surfaces into regression tests. Each case has a minimal project, `expected.json`, and `EXPECTED.md`.

| Case | Surface | Expected calibration |
| --- | --- | --- |
| [`django-management-command`](../benchmarks/fp-cases/django-management-command/) | Django filesystem command discovery | Command module and command entry symbols are not dead code. |
| [`fastapi-route`](../benchmarks/fp-cases/fastapi-route/) | Decorator route registration | Route handler is framework-managed. |
| [`package-public-api`](../benchmarks/fp-cases/package-public-api/) | `__init__.py` reexport and `__all__` | Public export suppresses origin unused-symbol. |
| [`optional-dependency-guard`](../benchmarks/fp-cases/optional-dependency-guard/) | Guarded optional import | No runtime or optional dependency violation. |
| [`type-checking-only-import`](../benchmarks/fp-cases/type-checking-only-import/) | `TYPE_CHECKING` import | Missing dependency is low-confidence type scope only. |
| [`namespace-package-ambiguity`](../benchmarks/fp-cases/namespace-package-ambiguity/) | PEP 420 multi-root ambiguity | Ambiguity is explicit; related dead-code stays low confidence. |
| [`protocol-class`](../benchmarks/fp-cases/protocol-class/) | Structural typing protocol | Protocol class is not unused implementation code. |
| [`dataclass-only-fields`](../benchmarks/fp-cases/dataclass-only-fields/) | Dataclass model shape | Data model class is framework/model managed. |
| [`celery-shared-task`](../benchmarks/fp-cases/celery-shared-task/) | Celery task autodiscovery | Task function is framework-managed; module uncertainty is low. |

This corpus is not exhaustive. New false positives should be reported with a minimal case that can be
added here before changing confidence, suppression, or framework heuristics.

## Recommended Interpretation

- Treat high-confidence findings as review priorities.
- Treat medium-confidence findings as likely useful but not automatic changes.
- Treat low-confidence findings as context for inspection.
- Never auto-delete low-confidence dead code without human review.
