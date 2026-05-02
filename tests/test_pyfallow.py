from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pyfallow
from pyfallow.analysis import analyze
from pyfallow.ast_index import index_file
from pyfallow.baseline import compare_with_baseline, create_baseline
from pyfallow.config import load_config
from pyfallow.dependencies import parse_dependency_declarations
from pyfallow.models import VERSION
from pyfallow.sarif import to_sarif


ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 15


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def run_cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pyfallow", *args],
        text=True,
        capture_output=True,
        env=env or {**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
        timeout=TIMEOUT,
    )


def validate_schema(schema: dict, value) -> None:
    refs = schema.get("$defs", {})

    def resolve(ref: str) -> dict:
        assert ref.startswith("#/$defs/")
        return refs[ref.rsplit("/", 1)[-1]]

    def check(node: dict, item, path: str) -> None:
        if "$ref" in node:
            check(resolve(node["$ref"]), item, path)
            return
        if "const" in node:
            assert item == node["const"], path
        if "enum" in node:
            assert item in node["enum"], path
        expected = node.get("type")
        if expected is not None:
            allowed = expected if isinstance(expected, list) else [expected]
            assert any(_type_matches(kind, item) for kind in allowed), path
        if isinstance(item, (int, float)) and "minimum" in node:
            assert item >= node["minimum"], path
        if node.get("type") == "object" or isinstance(item, dict):
            required = set(node.get("required", []))
            assert required <= set(item), path
            properties = node.get("properties", {})
            if node.get("additionalProperties") is False:
                assert set(item) <= set(properties), path
            for key, child in properties.items():
                if key in item:
                    check(child, item[key], f"{path}.{key}")
        if node.get("type") == "array" or isinstance(item, list):
            child = node.get("items")
            if child:
                for index, element in enumerate(item):
                    check(child, element, f"{path}[{index}]")

    check(schema, value, "$")


def _type_matches(kind: str, item) -> bool:
    return (
        (kind == "object" and isinstance(item, dict))
        or (kind == "array" and isinstance(item, list))
        or (kind == "string" and isinstance(item, str))
        or (kind == "integer" and isinstance(item, int) and not isinstance(item, bool))
        or (kind == "boolean" and isinstance(item, bool))
        or (kind == "null" and item is None)
        or (kind == "number" and isinstance(item, (int, float)) and not isinstance(item, bool))
    )


def make_fixture_project(tmp_path: Path) -> Path:
    write(
        tmp_path / "pyproject.toml",
        """
        [project]
        name = "demo"
        version = "0.1.0"
        dependencies = [
          "requests>=2",
          "pillow",
          "fastapi",
          "flask",
          "celery",
          "unusedpkg",
        ]

        [project.optional-dependencies]
        math = ["numpy"]

        [project.scripts]
        demo = "pkg.cli:main"

        [tool.poetry.group.dev.dependencies]
        pytest = "*"

        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/pkg/main.py"]
        include_tests = false

        [tool.pyfallow.dupes]
        min_lines = 3
        min_tokens = 10
        mode = "mild"

        [tool.pyfallow.health]
        max_cyclomatic = 3
        max_cognitive = 4
        max_function_lines = 20
        max_file_lines = 200
        hotspot_score_threshold = 20

        [[tool.pyfallow.boundaries.rules]]
        name = "domain-no-infra"
        from = "src/pkg/domain/**"
        disallow = ["src/pkg/infra/**", "pkg.infra.*"]
        severity = "error"
        """,
    )
    write(
        tmp_path / "requirements.txt",
        """
        flask
        """,
    )
    write(
        tmp_path / "src/pkg/__init__.py",
        """
        from .used import Used
        __all__ = ["Used"]
        """,
    )
    write(
        tmp_path / "src/pkg/main.py",
        """
        import importlib
        import requests
        import missingdist
        import numpy as np
        from PIL import Image
        from .used import Used, used_function
        from . import cycle_a

        NAME = "pkg.dynamic_unknown"
        importlib.import_module("pkg.dynamic_mod")
        importlib.import_module(NAME)

        def main():
            used_function()
            return Used(), requests.__name__, Image, np.__name__, missingdist
        """,
    )
    write(
        tmp_path / "src/pkg/used.py",
        """
        # fallow: ignore[unused-module]
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            import pandas as pd

        class Used:
            pass

        def used_function():
            return 1

        def unused_function():
            return 2

        def suppressed_unused():  # fallow: ignore[unused-symbol]
            return 3
        """,
    )
    write(
        tmp_path / "src/pkg/domain/service.py",
        """
        from pkg.infra.db import connect

        def complex_policy(value):
            total = 0
            if value > 10:
                for item in range(value):
                    if item % 2 and item > 3:
                        total += item
                    else:
                        total -= item
            elif value == 3:
                total = 3
            try:
                connect()
            except RuntimeError:
                total = -1
            return total
        """,
    )
    write(
        tmp_path / "src/pkg/infra/db.py",
        """
        def connect():
            return "ok"
        """,
    )
    write(tmp_path / "src/pkg/cycle_a.py", "from . import cycle_b\nVALUE_A = cycle_b.VALUE_B\n")
    write(tmp_path / "src/pkg/cycle_b.py", "from . import cycle_a\nVALUE_B = 1\n")
    write(tmp_path / "src/pkg/unused_mod.py", "def orphan():\n    return 'unused'\n")
    write(tmp_path / "src/pkg/dynamic_mod.py", "VALUE = 1\n")
    write(
        tmp_path / "src/pkg/api.py",
        """
        from fastapi import FastAPI

        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []
        """,
    )
    write(
        tmp_path / "src/pkg/flask_app.py",
        """
        from flask import Flask

        app = Flask(__name__)

        @app.route("/")
        def home():
            return "ok"
        """,
    )
    write(
        tmp_path / "src/pkg/tasks.py",
        """
        from celery import shared_task

        @shared_task
        def work():
            return 1
        """,
    )
    duplicate = """
        def duplicate_block(value):
            total = 0
            for item in range(value):
                if item % 2:
                    total += item
                else:
                    total -= item
            return total
    """
    write(tmp_path / "src/pkg/dupe1.py", duplicate)
    write(tmp_path / "src/pkg/dupe2.py", duplicate.replace("duplicate_block", "renamed_block"))
    write(tmp_path / "src/ns_pkg/mod.py", "VALUE = 1\n")
    write(tmp_path / "src/bad.py", "def broken(:\n    pass\n")
    write(
        tmp_path / "src/tests/test_app.py",
        """
        import pytest

        @pytest.fixture
        def sample():
            return 1

        def test_sample(sample):
            assert sample == 1
        """,
    )
    return tmp_path


def analyze_fixture(root: Path) -> dict:
    return analyze(load_config(root))


def rules(result: dict) -> set[str]:
    return {issue["rule"] for issue in result["issues"]}


def issues_for(result: dict, rule: str) -> list[dict]:
    return [issue for issue in result["issues"] if issue["rule"] == rule]


def test_full_analysis_reports_required_signals(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    result = analyze_fixture(root)

    assert result["tool"] == "fallow"
    assert result["language"] == "python"
    assert result["schema_version"] == "1.0"
    assert result["analysis"]["modules_analyzed"] >= 10
    assert "pkg.used" in {node["id"] for node in result["graphs"]["modules"]}
    assert "ns_pkg.mod" in {node["id"] for node in result["graphs"]["modules"]}
    assert {"fastapi", "flask", "celery", "pytest"} <= set(result["analysis"]["frameworks_detected"])

    found = rules(result)
    assert "parse-error" in found
    assert "dynamic-import" in found
    assert "circular-dependency" in found
    assert "unused-module" in found
    assert "unused-symbol" in found
    assert "missing-runtime-dependency" in found
    assert "unused-runtime-dependency" in found
    assert "optional-dependency-used-in-runtime" in found
    assert "duplicate-code" in found
    assert "high-cyclomatic-complexity" in found
    assert "high-cognitive-complexity" in found
    assert "boundary-violation" in found
    assert "stale-suppression" in found
    assert result["summary"]["duplicate_groups"] >= 1
    assert result["summary"]["boundary_violations"] == 1
    parse_errors = issues_for(result, "parse-error")
    assert parse_errors[0]["range"]["start"] == {"line": 1, "column": 12}
    assert not any(
        issue["path"] == "src/bad.py"
        and issue["rule"] in {"unused-module", "unused-symbol", "duplicate-code", "high-cyclomatic-complexity"}
        for issue in result["issues"]
    )


def test_import_resolution_dependency_mapping_and_type_checking(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    result = analyze_fixture(root)

    edges = {(edge["from"], edge["to"]) for edge in result["graphs"]["edges"]}
    assert ("pkg.main", "pkg.used") in edges
    assert ("pkg.main", "pkg.cycle_a") in edges
    assert ("pkg.cycle_a", "pkg.cycle_b") in edges

    missing = issues_for(result, "missing-runtime-dependency") + issues_for(result, "missing-type-dependency")
    assert any(issue["evidence"]["distribution"] == "missingdist" for issue in missing)
    pandas = [issue for issue in missing if issue["evidence"]["distribution"] == "pandas"]
    assert pandas and pandas[0]["severity"] == "info" and pandas[0]["confidence"] == "low"
    assert pandas[0]["evidence"]["policy"] == "type-only"
    assert not any(issue["evidence"].get("distribution") == "pillow" for issue in missing)
    assert any(issue["evidence"]["distribution"] == "numpy" for issue in issues_for(result, "optional-dependency-used-in-runtime"))
    assert any(issue["evidence"]["distribution"] == "unusedpkg" for issue in issues_for(result, "unused-runtime-dependency"))


def test_dead_code_is_conservative_for_exports_suppressions_and_frameworks(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    result = analyze_fixture(root)

    unused_symbols = {(issue["path"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("src/pkg/used.py", "unused_function") in unused_symbols
    assert ("src/pkg/used.py", "suppressed_unused") not in unused_symbols
    assert ("src/pkg/api.py", "list_items") not in unused_symbols
    assert ("src/pkg/flask_app.py", "home") not in unused_symbols
    assert ("src/pkg/tasks.py", "work") not in unused_symbols
    assert ("src/pkg/__init__.py", "Used") not in unused_symbols

    unused_modules = {issue["path"] for issue in issues_for(result, "unused-module")}
    assert "src/pkg/unused_mod.py" in unused_modules
    assert "src/pkg/__init__.py" not in unused_modules


def test_config_parsers_cover_pep621_poetry_and_requirements(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    declarations = parse_dependency_declarations(root)

    assert "requests" in declarations.runtime
    assert "pillow" in declarations.runtime
    assert "numpy" in declarations.optional
    assert "pytest" in declarations.dev
    assert "flask" in declarations.runtime
    assert "pkg.cli" in declarations.scripts
    assert ("pkg.cli", "main") in declarations.script_targets


def test_output_formats_baseline_and_agent_context(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    baseline_path = root / ".fallow-baseline.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    json_run = run_cli(["analyze", "--root", str(root), "--format", "json"], env)
    assert json_run.returncode == 0
    payload = json.loads(json_run.stdout)
    assert "summary" in payload and "metrics" in payload and "limitations" in payload

    default_run = run_cli(["--root", str(root), "--format", "json"], env)
    assert default_run.returncode == 0
    assert json.loads(default_run.stdout)["language"] == "python"

    sarif_run = run_cli(["analyze", "--root", str(root), "--format", "sarif"], env)
    assert sarif_run.returncode == 0
    sarif = json.loads(sarif_run.stdout)
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"]

    create_run = run_cli(
        [
            "baseline",
            "create",
            "--root",
            str(root),
            "--output",
            str(baseline_path),
            "--quiet",
        ],
        env,
    )
    assert create_run.returncode == 0
    assert baseline_path.exists()

    compare_run = run_cli(
        [
            "baseline",
            "compare",
            "--root",
            str(root),
            "--baseline",
            str(baseline_path),
            "--format",
            "json",
        ],
        env,
    )
    assert compare_run.returncode == 0
    compared = json.loads(compare_run.stdout)
    assert compared["baseline"]["new_count"] == 0
    assert compared["baseline"]["existing_count"] > 0

    context_run = run_cli(["agent-context", "--root", str(root), "--format", "markdown"], env)
    assert context_run.returncode == 0
    for heading in [
        "Project Overview",
        "Architecture Map",
        "Risk Map",
        "Dead Code Candidates",
        "Dependency Findings",
        "Suggested Agent Workflow",
        "Limitations",
    ]:
        assert heading in context_run.stdout


def test_release_metadata_version_schema_and_readme_examples() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyfallow.__version__ == pyproject["project"]["version"] == VERSION
    assert pyproject["project"]["version"] == "0.1.0-alpha.1"
    assert pyproject["project"]["dependencies"] == []

    for path in [
        ROOT / "schemas/pyfallow-report.schema.json",
        ROOT / "schemas/pyfallow-sarif.schema.json",
        ROOT / "examples/outputs/demo-report.excerpt.json",
        ROOT / "examples/outputs/demo.sarif.excerpt.json",
    ]:
        assert json.loads(path.read_text(encoding="utf-8"))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m pyfallow analyze --root examples/demo_project --format text" in readme
    assert "not currently an official fallow-rs/fallow project" in readme
    assert "Runtime dependencies are stdlib-only" in readme


def test_example_project_cli_commands_work() -> None:
    root = ROOT / "examples/demo_project"

    text_run = run_cli(["analyze", "--root", str(root), "--format", "text"])
    assert text_run.returncode == 0
    assert "PY040" in text_run.stdout
    assert "PY020" in text_run.stdout
    assert "PY070" in text_run.stdout

    json_run = run_cli(["--root", str(root), "--format", "json"])
    assert json_run.returncode == 0
    payload = json.loads(json_run.stdout)
    assert payload["language"] == "python"
    assert {"missing-runtime-dependency", "circular-dependency", "boundary-violation"} <= rules(payload)

    agent_run = run_cli(["agent-context", "--root", str(root), "--format", "markdown"])
    assert agent_run.returncode == 0
    assert "Project Overview" in agent_run.stdout


def test_self_audit_gate_is_clean_for_repository() -> None:
    result = run_cli(
        [
            "analyze",
            "--root",
            str(ROOT),
            "--fail-on",
            "warning",
            "--min-confidence",
            "medium",
        ]
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 issues" in result.stdout


def test_cli_exit_codes_and_focus_commands(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    no_fail = run_cli(["deps", "--root", str(root), "--format", "text"], env)
    assert no_fail.returncode == 0
    assert "PY040" in no_fail.stdout
    assert "PY060" not in no_fail.stdout

    fail_warning = run_cli(
        [
            "deps",
            "--root",
            str(root),
            "--fail-on",
            "warning",
            "--min-confidence",
            "medium",
        ],
        env,
    )
    assert fail_warning.returncode == 1

    parse_root = tmp_path / "only_bad"
    write(parse_root / "bad.py", "def broken(:\n    pass\n")
    parse_fail = run_cli(["analyze", "--root", str(parse_root), "--fail-on", "error"], env)
    assert parse_fail.returncode == 3

    changed_only = run_cli(
        [
            "analyze",
            "--root",
            str(root),
            "--changed-only",
            "--format",
            "json",
        ],
        env,
    )
    assert changed_only.returncode == 0
    payload = json.loads(changed_only.stdout)
    assert payload["analysis"]["changed_only"]["requested"] is True
    assert payload["analysis"]["changed_only"]["effective"] is False
    assert payload["analysis"]["warnings"][0]["code"] == "changed-only-unavailable"


def test_inferred_entrypoints_management_commands_and_no_boundary_violation(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]

        [[tool.pyfallow.boundaries.rules]]
        name = "domain-no-infra"
        from = "src/pkg/domain/**"
        disallow = ["src/pkg/infra/**"]
        severity = "error"
        """,
    )
    write(tmp_path / "src/app/main.py", "from pkg.domain.model import Model\n\ndef main():\n    return Model()\n")
    write(tmp_path / "src/pkg/domain/model.py", "class Model:\n    pass\n")
    write(tmp_path / "src/pkg/infra/db.py", "def connect():\n    return None\n")
    write(tmp_path / "src/pkg/management/commands/cleanup.py", "def handle():\n    return None\n")

    result = analyze_fixture(tmp_path)

    assert any(entry["module"] == "app.main" and entry["reason"] == "conventional-name" for entry in result["analysis"]["entrypoints"])
    assert "src/pkg/domain/model.py" not in {issue["path"] for issue in issues_for(result, "unused-module")}
    assert "src/pkg/management/commands/cleanup.py" not in {issue["path"] for issue in issues_for(result, "unused-module")}
    assert result["summary"]["boundary_violations"] == 0


def test_include_tests_keeps_pytest_fixtures_conservative(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    config = load_config(root)
    config.include_tests = True
    result = analyze(config)

    unused_symbols = {(issue["path"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("src/tests/test_app.py", "sample") not in unused_symbols


def test_visit_if_test_condition_records_name_references(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        ALLOWED = {"a", "b"}
        FALLBACK = "x"
        DEFAULT = 1

        def main(x):
            if x in ALLOWED:
                return FALLBACK
            elif DEFAULT and x:
                return DEFAULT
            return None
        """,
    )

    result = analyze_fixture(tmp_path)
    unused = {(issue["module"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("app", "ALLOWED") not in unused
    assert ("app", "FALLBACK") not in unused
    assert ("app", "DEFAULT") not in unused


def test_reexports_and_from_package_submodule_alias_usage(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/main.py"]

        [tool.pyfallow.dead_code]
        confidence_for_init_exports = "high"
        """,
    )
    write(
        tmp_path / "src/pkg/__init__.py",
        """
        from .model import Exported
        __all__ = ["Exported"]
        """,
    )
    write(
        tmp_path / "src/pkg/model.py",
        """
        class Exported:
            pass

        class Unused:
            pass
        """,
    )
    write(
        tmp_path / "src/pkg/submodule.py",
        """
        class Thing:
            pass

        class Other:
            pass
        """,
    )
    write(
        tmp_path / "src/main.py",
        """
        from pkg import Exported
        from pkg import submodule

        def main():
            return Exported(), submodule.Thing()
        """,
    )

    result = analyze_fixture(tmp_path)
    unused = {(issue["module"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("pkg.model", "Exported") not in unused
    assert ("pkg.submodule", "Thing") not in unused
    assert ("pkg.model", "Unused") in unused
    assert ("pkg.submodule", "Other") in unused
    exports = result["graphs"]["exports"]
    assert any(item["name"] == "Exported" and item["origin_module"] == "pkg.model" for item in exports)


def test_export_mutations_aliases_and_star_exports(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/main.py"]

        [tool.pyfallow.dead_code]
        confidence_for_init_exports = "high"
        """,
    )
    write(
        tmp_path / "src/pkg/__init__.py",
        """
        from .model import Original as PublicAlias
        from .extra import *
        __all__ = ["PublicAlias"]
        __all__ += ["Extra"]
        __all__.append("Appended")
        __all__.extend(["Extended"])
        """,
    )
    write(
        tmp_path / "src/pkg/model.py",
        """
        class Original:
            pass

        class Appended:
            pass

        class Extended:
            pass
        """,
    )
    write(
        tmp_path / "src/pkg/extra.py",
        """
        __all__ = ["Extra"]

        class Extra:
            pass
        """,
    )
    write(
        tmp_path / "src/main.py",
        """
        from pkg import PublicAlias, Extra

        def main():
            return PublicAlias(), Extra()
        """,
    )

    result = analyze_fixture(tmp_path)
    exports = result["graphs"]["exports"]
    assert any(item["name"] == "PublicAlias" and item["origin_symbol"] == "Original" and item["source"] == "direct-reexport" for item in exports)
    assert any(item["name"] == "Extra" and item["source"] == "star-reexport" and item["confidence"] == "high" for item in exports)
    assert any(item["name"] == "Appended" and item["source"] == "__all__-mutation" for item in exports)
    assert any(item["name"] == "Extended" and item["source"] == "__all__-mutation" for item in exports)
    model_node = next(module for module in result["graphs"]["modules"] if module["id"] == "pkg.model")
    original = next(symbol for symbol in model_node["symbols"] if symbol["name"] == "Original")
    appended = next(symbol for symbol in model_node["symbols"] if symbol["name"] == "Appended")
    assert original["state"]["public_api"] is True and original["state"]["referenced"] is True
    assert original["state"]["public_api_confidence"] == "high"
    assert appended["state"]["public_api"] is False and appended["state"]["referenced"] is False


def test_unknown_star_exports_lower_but_do_not_suppress_unused_symbol(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/main.py"]
        """,
    )
    write(tmp_path / "src/pkg/__init__.py", "from .unknown import *\n")
    write(tmp_path / "src/pkg/unknown.py", "class MaybePublic:\n    pass\n")
    write(tmp_path / "src/main.py", "import pkg\n\ndef main():\n    return pkg\n")

    result = analyze_fixture(tmp_path)
    unused = [issue for issue in issues_for(result, "unused-symbol") if issue["symbol"] == "MaybePublic"]
    assert unused and unused[0]["confidence"] == "low"
    node = next(module for module in result["graphs"]["modules"] if module["id"] == "pkg.unknown")
    symbol = next(item for item in node["symbols"] if item["name"] == "MaybePublic")
    assert symbol["state"]["public_api"] is True
    assert symbol["state"]["public_api_confidence"] == "low"
    assert symbol["state"]["dynamic_uncertain"] is True


def test_all_concat_getattr_and_namespace_ambiguity_are_reported(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src", "alt"]
        entry = ["src/main.py"]
        """,
    )
    write(
        tmp_path / "src/pkg/__init__.py",
        """
        from .model import A, B
        __all__ = ["A"] + ["B"]

        def __getattr__(name):
            raise AttributeError(name)
        """,
    )
    write(tmp_path / "src/pkg/model.py", "class A:\n    pass\n\nclass B:\n    pass\n")
    write(tmp_path / "src/pkg/amb.py", "VALUE = 'src'\n")
    write(tmp_path / "alt/pkg/amb.py", "VALUE = 'alt'\n")
    write(tmp_path / "src/main.py", "from pkg import A\n\ndef main():\n    return A()\n")

    result = analyze_fixture(tmp_path)
    exports = {(item["module"], item["name"]) for item in result["graphs"]["exports"]}
    assert ("pkg", "A") in exports
    assert ("pkg", "B") in exports
    package = next(module for module in result["graphs"]["modules"] if module["id"] == "pkg")
    assert package["state"]["dynamic_uncertain"] is True
    assert any(item["module"] == "pkg.amb" for item in result["analysis"]["module_ambiguities"])


def test_include_tests_false_does_not_leak_test_references_to_production(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        include_tests = false

        [tool.pyfallow.dependencies]
        include_dev = true
        """,
    )
    write(tmp_path / "src/app.py", "def main():\n    return 'ok'\n")
    write(tmp_path / "src/prod.py", "class OnlyTestsUse:\n    pass\n")
    write(tmp_path / "src/tests/test_prod.py", "from prod import OnlyTestsUse\n\ndef test_ref():\n    assert OnlyTestsUse\n")

    result = analyze_fixture(tmp_path)
    unused = {(issue["module"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("prod", "OnlyTestsUse") in unused
    edges = {(edge["from"], edge["to"]) for edge in result["graphs"]["edges"]}
    assert ("tests.test_prod", "prod") not in edges
    prod_node = next(module for module in result["graphs"]["modules"] if module["id"] == "prod")
    symbol = next(item for item in prod_node["symbols"] if item["name"] == "OnlyTestsUse")
    assert symbol["state"]["referenced"] is False
    assert symbol["state"]["referenced_by"] == {"production": 0, "tests": 1, "type_only": 0}


def test_production_importing_test_code_is_reported_without_graph_edge(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        include_tests = false

        [tool.pyfallow.dependencies]
        include_dev = true
        """,
    )
    write(tmp_path / "src/app.py", "from tests.helpers import helper\n\ndef main():\n    return helper()\n")
    write(tmp_path / "src/tests/helpers.py", "def helper():\n    return 1\n")

    result = analyze_fixture(tmp_path)
    assert any(issue["rule"] == "production-imports-test-code" for issue in result["issues"])
    edges = {(edge["from"], edge["to"]) for edge in result["graphs"]["edges"]}
    assert ("app", "tests.helpers") not in edges


def test_test_duplicates_and_complexity_are_skipped_when_tests_excluded(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        include_tests = false

        [tool.pyfallow.dupes]
        min_lines = 3
        min_tokens = 8

        [tool.pyfallow.health]
        max_cyclomatic = 2
        max_cognitive = 2
        """,
    )
    write(tmp_path / "src/app.py", "def main():\n    return 1\n")
    block = """
        def test_complex(value):
            total = 0
            if value:
                for item in range(value):
                    if item % 2:
                        total += item
            return total
    """
    write(tmp_path / "src/tests/test_one.py", block)
    write(tmp_path / "src/tests/test_two.py", block.replace("test_complex", "test_other"))

    result = analyze_fixture(tmp_path)
    assert not issues_for(result, "duplicate-code")
    assert not [
        issue
        for issue in result["issues"]
        if issue["rule"] in {"high-cyclomatic-complexity", "high-cognitive-complexity"}
    ]

    config = load_config(tmp_path)
    config.include_tests = True
    included = analyze(config)
    assert issues_for(included, "duplicate-code")
    assert any(
        issue["path"].startswith("src/tests/")
        for issue in included["issues"]
        if issue["rule"] in {"high-cyclomatic-complexity", "high-cognitive-complexity"}
    )


def test_packaging_script_target_symbol_is_used(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [project.scripts]
        demo = "pkg.cli:main"

        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/other.py"]
        """,
    )
    write(tmp_path / "src/pkg/__init__.py", "__all__ = []\n")
    write(
        tmp_path / "src/pkg/cli.py",
        """
        def main():
            return 0

        def helper():
            return 1
        """,
    )
    write(tmp_path / "src/other.py", "def main():\n    return 2\n")

    result = analyze_fixture(tmp_path)
    unused = {(issue["module"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("pkg.cli", "main") not in unused
    assert ("pkg.cli", "helper") in unused


def test_configured_entry_symbols_are_entrypoint_managed(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]

        [tool.pyfallow.dead_code]
        entry_symbols = ["serve"]
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        def serve():
            return 1

        def helper():
            return 2
        """,
    )

    result = analyze_fixture(tmp_path)
    unused = {(issue["module"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("app", "serve") not in unused
    assert ("app", "helper") in unused


def test_dependency_policy_defaults(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [project]
        dependencies = ["runtimeonly"]

        [tool.poetry.group.dev.dependencies]
        devonly = "*"

        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        include_tests = false

        [tool.pyfallow.dependencies]
        include_dev = true
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        from typing import TYPE_CHECKING
        import devonly

        if TYPE_CHECKING:
            import typeonly

        def main():
            return devonly.__name__
        """,
    )
    write(tmp_path / "src/tests/test_deps.py", "import testonly\nimport runtimeonly\n")

    result = analyze_fixture(tmp_path)
    missing = (
        issues_for(result, "dev-dependency-used-in-runtime")
        + issues_for(result, "missing-type-dependency")
        + issues_for(result, "missing-test-dependency")
    )
    assert any(issue["evidence"]["distribution"] == "devonly" and issue["evidence"]["policy"] == "dev-declared-runtime-use" for issue in missing)
    typeonly = [issue for issue in issues_for(result, "missing-type-dependency") if issue["evidence"]["distribution"] == "typeonly"]
    assert typeonly and typeonly[0]["severity"] == "info" and typeonly[0]["confidence"] == "low"
    assert not any(issue["evidence"].get("distribution") == "testonly" for issue in missing)

    unused = issues_for(result, "runtime-dependency-used-only-in-tests")
    assert any(issue["evidence"]["distribution"] == "runtimeonly" and issue["evidence"]["policy"] == "test-only" for issue in unused)


def test_dependency_include_optional_and_dev_knobs_are_observable(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [project.optional-dependencies]
        speedups = ["orjson"]

        [tool.poetry.group.dev.dependencies]
        devonly = "*"

        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]

        [tool.pyfallow.dependencies]
        include_optional = false
        include_dev = false
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        import devonly
        import orjson

        def main():
            return devonly.__name__, orjson.__name__
        """,
    )

    result = analyze_fixture(tmp_path)
    missing = {issue["evidence"]["distribution"] for issue in issues_for(result, "missing-runtime-dependency")}
    assert {"devonly", "orjson"} <= missing
    assert not issues_for(result, "dev-dependency-used-in-runtime")
    assert not issues_for(result, "optional-dependency-used-in-runtime")

    config = load_config(tmp_path)
    config.dependencies.include_optional = True
    config.dependencies.include_dev = True
    included = analyze(config)
    assert any(issue["evidence"]["distribution"] == "devonly" for issue in issues_for(included, "dev-dependency-used-in-runtime"))
    assert any(issue["evidence"]["distribution"] == "orjson" for issue in issues_for(included, "optional-dependency-used-in-runtime"))


def test_guarded_optional_import_does_not_count_as_runtime_violation(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [project.optional-dependencies]
        speedups = ["orjson"]

        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        try:
            import orjson
        except ImportError:
            orjson = None

        def main():
            return orjson
        """,
    )

    result = analyze_fixture(tmp_path)
    assert not issues_for(result, "optional-dependency-used-in-runtime")
    assert not issues_for(result, "missing-runtime-dependency")


def test_tuple_import_error_guard_marks_imports_guarded(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [project.optional-dependencies]
        speedups = ["orjson"]

        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        try:
            import orjson
        except (ImportError, ModuleNotFoundError):
            orjson = None

        def main():
            return orjson
        """,
    )

    indexed = index_file(tmp_path / "src/app.py", tmp_path, "app", "src", False)
    imports = [record for record in indexed.imports if record.raw_module == "orjson"]
    assert imports and all(record.guarded for record in imports)

    result = analyze_fixture(tmp_path)
    assert not issues_for(result, "optional-dependency-used-in-runtime")
    assert not issues_for(result, "missing-runtime-dependency")


def test_namespace_protocol_dunder_and_init_export_knobs_are_observable(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]
        namespace_packages = false

        [tool.pyfallow.dead_code]
        ignore_protocol_methods = false
        ignore_dunder_methods = false
        confidence_for_init_exports = "medium"
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        import pkg

        def main():
            return pkg
        """,
    )
    write(tmp_path / "src/ns/mod.py", "VALUE = 1\n")
    write(tmp_path / "src/pkg/__init__.py", "from .model import Public\n__all__ = ['Public']\n")
    write(
        tmp_path / "src/pkg/model.py",
        """
        from typing import Protocol

        class Public:
            pass

        class Service(Protocol):
            pass

        __magic__ = 1
        """,
    )

    result = analyze_fixture(tmp_path)
    modules = {node["id"] for node in result["graphs"]["modules"]}
    assert "ns.mod" not in modules
    unused = {(issue["module"], issue.get("symbol")) for issue in issues_for(result, "unused-symbol")}
    assert ("pkg.model", "Public") not in unused
    assert ("pkg.model", "Service") in unused
    assert ("pkg.model", "__magic__") in unused
    public = next(
        symbol
        for node in result["graphs"]["modules"]
        if node["id"] == "pkg.model"
        for symbol in node["symbols"]
        if symbol["name"] == "Public"
    )
    assert public["state"]["public_api_confidence"] == "medium"


def test_cli_debug_and_show_limitations_flags_are_observable(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "def main():\n    return 1\n")

    debug_run = run_cli(["analyze", "--root", str(tmp_path), "--changed-only", "--debug", "--format", "json"])
    assert debug_run.returncode == 0
    assert "pyfallow DEBUG: analysis warning:" in debug_run.stderr

    limitations_run = run_cli(["analyze", "--root", str(tmp_path), "--format", "text", "--show-limitations"])
    assert limitations_run.returncode == 0
    assert "Limitations:" in limitations_run.stdout
    assert "Dynamic imports" in limitations_run.stdout


def test_nested_function_complexity_does_not_inflate_parent(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]
        entry = ["src/app.py"]

        [tool.pyfallow.health]
        max_cyclomatic = 3
        max_cognitive = 4
        """,
    )
    write(
        tmp_path / "src/app.py",
        """
        def main():
            def nested(value):
                if value:
                    for item in range(value):
                        if item % 2:
                            return item
                return 0
            return nested(3)
        """,
    )

    result = analyze_fixture(tmp_path)
    complexity = [
        issue
        for issue in result["issues"]
        if issue["rule"] in {"high-cyclomatic-complexity", "high-cognitive-complexity"}
    ]
    assert not any(issue["symbol"] == "main" for issue in complexity)
    assert any(issue["symbol"] == "nested" for issue in complexity)


def test_config_validation_emits_config_error(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.pyfallow]
        roots = ["src"]

        [tool.pyfallow.dupes]
        mode = "wild"
        min_tokens = 0

        [tool.pyfallow.health]
        max_cognitive = 0

        [[tool.pyfallow.boundaries.rules]]
        name = "bad"
        from = []
        disallow = []
        severity = "fatal"
        """,
    )
    write(tmp_path / "src/app.py", "VALUE = 1\n")

    result = analyze_fixture(tmp_path)
    config_errors = issues_for(result, "config-error")
    assert len(config_errors) >= 4
    assert result["summary"]["config_errors"] == len(config_errors)
    config = load_config(tmp_path)
    assert config.dupes.min_tokens == 40
    assert config.dupes.mode == "mild"
    assert config.health.max_cognitive == 15


def test_sarif_has_fingerprints_properties_and_related_locations(tmp_path: Path, monkeypatch) -> None:
    root = make_fixture_project(tmp_path)
    result = analyze_fixture(root)
    monkeypatch.chdir(root)
    sarif = to_sarif(result)
    sarif_results = sarif["runs"][0]["results"]
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]

    assert all("primaryLocationLineHash" in item["partialFingerprints"] for item in sarif_results)
    assert all("precision" in item["properties"] and "problem.severity" in item["properties"] for item in rules)
    assert any(item["properties"]["problem.severity"] == "recommendation" for item in rules)
    assert sarif["runs"][0]["automationDetails"]["id"] == "pyfallow/python/"
    assert all("endLine" in item["locations"][0]["physicalLocation"]["region"] for item in sarif_results)
    cycle = next(item for item in sarif_results if item["ruleId"] == "PY020")
    assert cycle["relatedLocations"]
    duplicate = next(item for item in sarif_results if item["ruleId"] == "PY050")
    assert duplicate["relatedLocations"]
    capped = to_sarif(result, max_related_locations=1)
    assert all(len(item.get("relatedLocations", [])) <= 1 for item in capped["runs"][0]["results"])
    missing = next(item for item in result["issues"] if item["rule"] == "missing-runtime-dependency")
    expected_line = (root / missing["path"]).read_text(encoding="utf-8").splitlines()[missing["range"]["start"]["line"] - 1]
    expected_hash = hashlib.sha1(" ".join(expected_line.strip().split()).encode("utf-8")).hexdigest()
    sarif_missing = next(item for item in sarif_results if item["partialFingerprints"]["pyfallowFingerprint"] == missing["fingerprint"])
    assert sarif_missing["partialFingerprints"]["primaryLocationLineHash"] == expected_hash


def test_sarif_schema_and_golden_fixture_contract() -> None:
    result = analyze_fixture(ROOT / "tests/fixtures/demo_project")
    sarif = to_sarif(result)
    schema = json.loads((ROOT / "schemas/pyfallow-sarif.schema.json").read_text(encoding="utf-8"))
    validate_schema(schema, sarif)
    subset = {
        "version": sarif["version"],
        "automation_id": sarif["runs"][0]["automationDetails"]["id"],
        "rule_ids": sorted(rule["id"] for rule in sarif["runs"][0]["tool"]["driver"]["rules"]),
        "result_rule_ids": sorted({item["ruleId"] for item in sarif["runs"][0]["results"]}),
        "has_related": any(
            item.get("relatedLocations")
            for item in sarif["runs"][0]["results"]
            if item["ruleId"] in {"PY020", "PY050"}
        ),
    }
    golden = json.loads((ROOT / "tests/golden/demo_project_sarif_golden.json").read_text(encoding="utf-8"))
    assert subset == golden


def test_baseline_helpers_classify_existing_new_and_resolved(tmp_path: Path) -> None:
    root = make_fixture_project(tmp_path)
    result = analyze_fixture(root)
    baseline = create_baseline(result)
    comparison = compare_with_baseline([], baseline)
    assert comparison["resolved_count"] == len(baseline["issues"])

    comparison = compare_with_baseline(
        [type("IssueLike", (), {"fingerprint": result["issues"][0]["fingerprint"]})()],
        baseline,
    )
    assert comparison["existing_count"] == 1
    assert comparison["resolved_count"] == len(baseline["issues"]) - 1


def test_json_schema_and_golden_fixture_contract() -> None:
    schema = json.loads((ROOT / "schemas/pyfallow-report.schema.json").read_text(encoding="utf-8"))
    result = analyze_fixture(ROOT / "tests/fixtures/demo_project")

    validate_schema(schema, result)
    assert set(schema["required"]) <= set(result)
    assert set(schema["properties"]["analysis"]["required"]) <= set(result["analysis"])
    assert set(schema["properties"]["summary"]["required"]) <= set(result["summary"])
    assert set(schema["properties"]["graphs"]["required"]) <= set(result["graphs"])
    assert all(issue["severity"] in {"info", "warning", "error"} for issue in result["issues"])
    assert all(issue["confidence"] in {"low", "medium", "high"} for issue in result["issues"])

    actual = {
        "summary": result["summary"],
        "rules": sorted({issue["rule"] for issue in result["issues"]}),
        "edges": [[edge["from"], edge["to"]] for edge in result["graphs"]["edges"]],
    }
    golden = json.loads((ROOT / "tests/golden/demo_project_report_golden.json").read_text(encoding="utf-8"))
    assert actual == golden
