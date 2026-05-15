from __future__ import annotations

from .models import ModuleInfo


def detect_frameworks(modules: dict[str, ModuleInfo], declared: set[str]) -> list[str]:
    found: set[str] = set()
    for dep in declared:
        if dep in {"django", "fastapi", "flask", "celery", "pytest", "click", "typer", "sqlalchemy", "pydantic"}:
            found.add(dep)
    for module in modules.values():
        found.update(module.framework_hints)
        name = module.path.rsplit("/", 1)[-1]
        if module.path == "manage.py" or name in {"settings.py", "urls.py", "asgi.py", "wsgi.py"}:
            found.add("django")
        if name == "conftest.py" or name.startswith("test_"):
            found.add("pytest")
        if "/management/commands/" in f"/{module.path}":
            found.add("django")
        for record in module.imports:
            top = (record.raw_module or "").split(".", 1)[0]
            if top in {"django", "fastapi", "flask", "celery", "pytest", "click", "typer", "sqlalchemy", "pydantic"}:
                found.add(top)
    return sorted(found)
