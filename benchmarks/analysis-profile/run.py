from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


BENCH_DIR = Path(__file__).resolve().parent
ROOT = BENCH_DIR.parents[1]
SRC = ROOT / "src"
DEFAULT_WORKSPACE = BENCH_DIR / "workspace"
DEFAULT_OUTPUT = BENCH_DIR / "results" / "analysis-profile.json"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass(frozen=True, slots=True)
class ProfileCase:
    name: str
    description: str
    root: Path | None


CASES = [
    ProfileCase(
        name="demo-project",
        description="Checked-in demo project with dependency, graph, duplicate, and boundary findings.",
        root=ROOT / "examples" / "demo_project",
    ),
    ProfileCase(
        name="generated",
        description="Generated pure-Python fixture sized with --generated-modules.",
        root=None,
    ),
]

PHASES = [
    "source_discovery",
    "file_indexing",
    "module_resolution",
    "dependency_analysis",
    "graph_analysis",
    "boundary_analysis",
    "duplicate_detection",
    "dead_code_analysis",
    "complexity_analysis",
    "suppressions_fingerprints",
    "format_serialization",
]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        print(json.dumps(list_cases(), indent=2, sort_keys=True))
        return 0

    selected = select_cases(args.case)
    payload = {
        "schema_version": "1.0",
        "runs_requested": args.runs,
        "generated_modules": args.generated_modules,
        "cases": [
            profile_case(case, args.runs, args.workspace, args.generated_modules)
            for case in selected
        ],
    }
    write_output(args.output, payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile pyfallow analyzer phases before considering parallel AST indexing."
    )
    parser.add_argument("--case", default="all", help="demo-project, generated, or all.")
    parser.add_argument("--runs", type=positive_int, default=3)
    parser.add_argument("--generated-modules", type=positive_int, default=120)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path, or '-' for stdout.")
    parser.add_argument("--list", action="store_true", help="Print configured profile cases as JSON.")
    return parser


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def list_cases() -> dict[str, Any]:
    return {
        "cases": [
            {
                "name": case.name,
                "description": case.description,
                "root": str(case.root.relative_to(ROOT)) if case.root else None,
            }
            for case in CASES
        ],
        "phases": PHASES,
    }


def select_cases(name: str) -> list[ProfileCase]:
    if name == "all":
        return CASES
    selected = [case for case in CASES if case.name == name]
    if not selected:
        choices = ", ".join(case.name for case in CASES)
        raise SystemExit(f"Unknown case {name!r}; expected one of: {choices}, all")
    return selected


def profile_case(case: ProfileCase, runs: int, workspace: Path, generated_modules: int) -> dict[str, Any]:
    case_root = prepare_case(case, workspace, generated_modules)
    run_payloads = [profile_once(case_root) for _ in range(runs)]
    total_seconds = [item["total_seconds"] for item in run_payloads]
    return {
        "case": case.name,
        "description": case.description,
        "root": str(case_root.relative_to(ROOT)) if case_root.is_relative_to(ROOT) else str(case_root),
        "repo_metrics": run_payloads[-1]["repo_metrics"],
        "summary": run_payloads[-1]["summary"],
        "median_total_seconds": round(statistics.median(total_seconds), 6),
        "median_phases": median_phases(run_payloads),
        "runs": run_payloads,
    }


def prepare_case(case: ProfileCase, workspace: Path, generated_modules: int) -> Path:
    if case.root:
        return case.root
    generated_root = workspace / f"generated-{generated_modules}"
    write_generated_fixture(generated_root, generated_modules)
    return generated_root


def write_generated_fixture(root: Path, modules: int) -> None:
    if root.exists():
        shutil.rmtree(root)
    package = root / "src" / "generated_app"
    package.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.pyfallow]",
                'roots = ["src"]',
                'entry = ["src/generated_app/main.py"]',
                "",
                "[tool.pyfallow.health]",
                "max_cyclomatic = 25",
                "max_cognitive = 60",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    imports = [f"from . import mod_{index:04d}" for index in range(0, modules, 5)]
    calls = [f"    total += mod_{index:04d}.work_{index:04d}(seed)" for index in range(0, modules, 5)]
    (package / "main.py").write_text(
        "\n".join(
            [
                *imports,
                "",
                "def main(seed: int = 1) -> int:",
                "    total = 0",
                *calls,
                "    return total",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for index in range(modules):
        previous_import = f"from . import mod_{index - 1:04d}" if index and index % 7 == 0 else ""
        previous_call = f"    value += mod_{index - 1:04d}.work_{index - 1:04d}(seed)" if index and index % 7 == 0 else ""
        (package / f"mod_{index:04d}.py").write_text(
            "\n".join(
                line
                for line in [
                    previous_import,
                    "",
                    f"def work_{index:04d}(seed: int) -> int:",
                    f"    value = seed + {index}",
                    "    if value % 2:",
                    "        value += 1",
                    previous_call,
                    "    return value",
                    "",
                    f"def duplicate_shape_{index:04d}(items):",
                    "    total = 0",
                    "    for item in items:",
                    "        if item:",
                    "            total += item",
                    "    return total",
                    "",
                ]
                if line
            ),
            encoding="utf-8",
        )


def profile_once(root: Path) -> dict[str, Any]:
    from pyfallow.analysis import analyze
    from pyfallow.config import load_config

    timers: dict[str, float] = defaultdict(float)
    config = load_config(root)
    started = time.perf_counter()
    with profiling_hooks(timers):
        report = analyze(config)
    total_seconds = time.perf_counter() - started
    serialization_started = time.perf_counter()
    json.dumps(report, sort_keys=True)
    timers["format_serialization"] += time.perf_counter() - serialization_started
    return {
        "total_seconds": round(total_seconds, 6),
        "phases": phase_rows(timers),
        "repo_metrics": {
            "files_analyzed": report["analysis"]["files_analyzed"],
            "modules_analyzed": report["analysis"]["modules_analyzed"],
            "symbols_indexed": report["analysis"]["symbols_indexed"],
            "imports_indexed": report["analysis"]["imports_indexed"],
            "issues": len(report["issues"]),
        },
        "summary": report["summary"],
    }


@contextmanager
def profiling_hooks(timers: dict[str, float]) -> Iterator[None]:
    import pyfallow.analysis as analysis
    import pyfallow.resolver as resolver

    patches: list[tuple[Any, str, Any]] = []

    def patch(obj: Any, name: str, phase: str) -> None:
        original = getattr(obj, name)

        def timed(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                timers[phase] += time.perf_counter() - started

        patches.append((obj, name, original))
        setattr(obj, name, timed)

    for name in ["discover_source_roots", "discover_python_files"]:
        patch(analysis, name, "source_discovery")
    patch(analysis, "index_file", "file_indexing")
    for name in ["module_name_for_path", "register", "resolve_import"]:
        patch(resolver.ModuleResolver, name, "module_resolution")
    for name in [
        "classify_imports",
        "parse_dependency_declarations",
        "entrypoints_from_packaging",
        "dependency_issues",
    ]:
        patch(analysis, name, "dependency_analysis")
    for name in ["build_import_graph", "strongly_connected_components", "_cycle_issues"]:
        patch(analysis, name, "graph_analysis")
    patch(analysis, "boundary_issues", "boundary_analysis")
    patch(analysis, "duplicate_issues", "duplicate_detection")
    patch(analysis, "dead_code_issues", "dead_code_analysis")
    patch(analysis, "analyze_complexity", "complexity_analysis")
    for name in ["apply_suppressions", "assign_fingerprints"]:
        patch(analysis, name, "suppressions_fingerprints")

    try:
        yield
    finally:
        for obj, name, original in reversed(patches):
            setattr(obj, name, original)


def median_phases(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_phase: dict[str, list[float]] = {phase: [] for phase in PHASES}
    for run in runs:
        for row in run["phases"]:
            by_phase[row["phase"]].append(row["seconds"])
    return [
        {"phase": phase, "seconds": round(statistics.median(values or [0.0]), 6)}
        for phase, values in by_phase.items()
    ]


def phase_rows(timers: dict[str, float]) -> list[dict[str, Any]]:
    return [{"phase": phase, "seconds": round(timers.get(phase, 0.0), 6)} for phase in PHASES]


def write_output(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if str(path) == "-":
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
