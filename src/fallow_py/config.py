from __future__ import annotations

import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import posix_path


DEFAULT_IGNORE = [
    ".git/**",
    ".hg/**",
    ".svn/**",
    ".venv/**",
    "venv/**",
    "env/**",
    "__pycache__/**",
    ".mypy_cache/**",
    ".pytest_cache/**",
    ".ruff_cache/**",
    "build/**",
    "dist/**",
    "*.egg-info/**",
    "site-packages/**",
    "node_modules/**",
]

DEFAULT_IMPORT_MAP = {
    "PIL": "pillow",
    "yaml": "pyyaml",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "Crypto": "pycryptodome",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "OpenSSL": "pyopenssl",
    "google.protobuf": "protobuf",
    "grpc": "grpcio",
    "lxml": "lxml",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "pandas": "pandas",
    "sqlalchemy": "sqlalchemy",
    "skimage": "scikit-image",
    "torch": "torch",
}


class ConfigError(ValueError):
    """User-supplied pyfallow configuration or contract data is malformed."""


@dataclass(slots=True)
class BoundaryRule:
    name: str
    from_patterns: list[str]
    disallow: list[str]
    severity: str = "warning"


@dataclass(slots=True)
class DeadCodeConfig:
    enabled: bool = True
    detect_unused_modules: bool = True
    detect_unused_symbols: bool = True
    treat_init_as_entry: bool = True
    ignore_symbols: list[str] = field(
        default_factory=lambda: ["__version__", "__all__", "Meta", "Config", "Settings"]
    )
    ignore_decorated: bool = True
    ignore_protocol_methods: bool = True
    ignore_dunder_methods: bool = True
    confidence_for_init_exports: str = "low"
    entry_symbols: list[str] = field(
        default_factory=lambda: [
            "main",
            "run",
            "app",
            "application",
            "handler",
            "lambda_handler",
            "handle",
            "cli",
            "create_app",
        ]
    )


@dataclass(slots=True)
class DependenciesConfig:
    enabled: bool = True
    check_unused: bool = True
    check_missing: bool = True
    include_optional: bool = True
    include_dev: bool = False
    report_type_only_missing: bool = True
    report_test_only_missing: bool = False
    ignore: list[str] = field(
        default_factory=lambda: ["pytest", "mypy", "ruff", "black", "coverage"]
    )
    import_map: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_IMPORT_MAP))


@dataclass(slots=True)
class DupesConfig:
    enabled: bool = True
    mode: str = "mild"
    min_lines: int = 6
    min_tokens: int = 40
    max_groups: int = 200
    ignore_docstrings: bool = True


@dataclass(slots=True)
class HealthConfig:
    enabled: bool = True
    max_cyclomatic: int = 10
    max_cognitive: int = 15
    max_function_lines: int = 80
    max_file_lines: int = 800
    hotspot_score_threshold: int = 50


@dataclass(slots=True)
class BaselineConfig:
    path: str = ".fallow-baseline.json"


@dataclass(slots=True)
class PythonConfig:
    root: Path
    config_path: Path | None = None
    roots: list[str] = field(default_factory=list)
    entry: list[str] = field(default_factory=list)
    include_tests: bool = False
    namespace_packages: bool = True
    framework_heuristics: bool = True
    frameworks: list[str] = field(default_factory=lambda: ["auto"])
    ignore: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE))
    dead_code: DeadCodeConfig = field(default_factory=DeadCodeConfig)
    dependencies: DependenciesConfig = field(default_factory=DependenciesConfig)
    dupes: DupesConfig = field(default_factory=DupesConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    baseline: BaselineConfig = field(default_factory=BaselineConfig)
    boundary_rules: list[BoundaryRule] = field(default_factory=list)
    config_errors: list[dict[str, str]] = field(default_factory=list)
    since_ref: str | None = None
    changed_only_requested: bool = False
    changed_only_alias: bool = False
    changed_only_effective: bool = False
    analysis_warnings: list[dict[str, str]] = field(default_factory=list)


def load_config(root: str | Path = ".", config_path: str | Path | None = None) -> PythonConfig:
    root_path = Path(root).resolve()
    selected_from_argument = config_path is not None
    selected: Path | None = Path(config_path).resolve() if config_path else None
    data: dict[str, Any] = {}
    if selected:
        if not selected.exists():
            raise FileNotFoundError(f"Config file does not exist: {selected}")
        data = _read_toml(selected)
    else:
        for candidate in (
            root_path / ".fallow-py.toml",
            root_path / ".fallow.toml",
            root_path / ".pyfallow.toml",
            root_path / "pyproject.toml",
        ):
            if candidate.exists():
                maybe = _extract_config(_read_toml(candidate), candidate.name)
                if maybe:
                    selected = candidate
                    data = maybe
                    break
    if selected and selected.name == "pyproject.toml" and selected_from_argument:
        data = _extract_config(_read_toml(selected), "pyproject.toml")
    elif selected and selected.name in {".fallow-py.toml", ".fallow.toml", ".pyfallow.toml"}:
        if selected.name == ".pyfallow.toml":
            _warn_legacy_config(".pyfallow.toml", ".fallow-py.toml")
        raw = _read_toml(selected)
        data = _extract_config(raw, selected.name) or raw
    return build_config(root_path, selected, data)


def build_config(root: Path, config_path: Path | None, data: dict[str, Any]) -> PythonConfig:
    _validate_config_types(data, config_path)
    cfg = PythonConfig(root=root, config_path=config_path)
    for key in (
        "roots",
        "entry",
        "include_tests",
        "namespace_packages",
        "framework_heuristics",
        "frameworks",
        "ignore",
    ):
        if key in data:
            setattr(cfg, key, _list_or_value(data[key]) if key in {"roots", "entry", "frameworks", "ignore"} else data[key])

    _merge_dataclass(cfg.dead_code, data.get("dead_code", {}))
    _merge_dataclass(cfg.dependencies, data.get("dependencies", {}))
    if "import_map" in data.get("dependencies", {}):
        cfg.dependencies.import_map.update(data["dependencies"]["import_map"])
    _merge_dataclass(cfg.dupes, data.get("dupes", {}))
    _merge_dataclass(cfg.health, data.get("health", {}))
    _merge_dataclass(cfg.baseline, data.get("baseline", {}))

    rules = data.get("boundaries", {}).get("rules", [])
    cfg.boundary_rules = []
    for raw in rules:
        from_value = raw.get("from", raw.get("from_patterns", []))
        cfg.boundary_rules.append(
            BoundaryRule(
                name=str(raw.get("name", "boundary-rule")),
                from_patterns=_list_or_value(from_value),
                disallow=_list_or_value(raw.get("disallow", [])),
                severity=str(raw.get("severity", "warning")),
            )
        )
    cfg.roots = [posix_path(item) for item in cfg.roots]
    cfg.entry = [posix_path(item) for item in cfg.entry]
    _validate(cfg)
    return cfg


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _extract_config(raw: dict[str, Any], name: str) -> dict[str, Any]:
    if name == "pyproject.toml":
        tool = raw.get("tool", {})
        fallow_py = tool.get("fallow_py")
        fallow_python = tool.get("fallow", {}).get("python")
        pyfallow = tool.get("pyfallow")
        if pyfallow and not fallow_py and not fallow_python:
            _warn_legacy_config("[tool.pyfallow]", "[tool.fallow_py]")
        return fallow_py or fallow_python or pyfallow or {}
    tool = raw.get("tool", {})
    fallow_py = tool.get("fallow_py")
    fallow_python = tool.get("fallow", {}).get("python")
    pyfallow = tool.get("pyfallow")
    if pyfallow and not fallow_py and not fallow_python:
        _warn_legacy_config("[tool.pyfallow]", "[tool.fallow_py]")
    return fallow_py or fallow_python or pyfallow or raw


def _warn_legacy_config(old: str, new: str) -> None:
    warnings.warn(
        f"{old} is deprecated; use {new} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def _merge_dataclass(target: object, values: dict[str, Any]) -> None:
    for key, value in values.items():
        if hasattr(target, key) and key != "import_map":
            setattr(target, key, value)


def _list_or_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _validate_config_types(data: dict[str, Any], config_path: Path | None) -> None:
    for key in ("roots", "entry", "frameworks", "ignore"):
        if key in data:
            _expect_str_list(config_path, key, data[key])
    for key in ("include_tests", "namespace_packages", "framework_heuristics"):
        if key in data:
            _expect_bool(config_path, key, data[key])

    _validate_section(
        data,
        config_path,
        "dead_code",
        {
            "enabled": _expect_bool,
            "detect_unused_modules": _expect_bool,
            "detect_unused_symbols": _expect_bool,
            "treat_init_as_entry": _expect_bool,
            "ignore_symbols": _expect_str_list,
            "ignore_decorated": _expect_bool,
            "ignore_protocol_methods": _expect_bool,
            "ignore_dunder_methods": _expect_bool,
            "confidence_for_init_exports": _expect_str,
            "entry_symbols": _expect_str_list,
        },
    )
    _validate_section(
        data,
        config_path,
        "dependencies",
        {
            "enabled": _expect_bool,
            "check_unused": _expect_bool,
            "check_missing": _expect_bool,
            "include_optional": _expect_bool,
            "include_dev": _expect_bool,
            "report_type_only_missing": _expect_bool,
            "report_test_only_missing": _expect_bool,
            "ignore": _expect_str_list,
            "import_map": _expect_str_dict,
        },
    )
    _validate_section(
        data,
        config_path,
        "dupes",
        {
            "enabled": _expect_bool,
            "mode": _expect_str,
            "min_lines": _expect_int,
            "min_tokens": _expect_int,
            "max_groups": _expect_int,
            "ignore_docstrings": _expect_bool,
        },
    )
    _validate_section(
        data,
        config_path,
        "health",
        {
            "enabled": _expect_bool,
            "max_cyclomatic": _expect_int,
            "max_cognitive": _expect_int,
            "max_function_lines": _expect_int,
            "max_file_lines": _expect_int,
            "hotspot_score_threshold": _expect_int,
        },
    )
    _validate_section(data, config_path, "baseline", {"path": _expect_str})
    _validate_boundaries_section(data, config_path)


def _validate_section(
    data: dict[str, Any],
    config_path: Path | None,
    name: str,
    validators: dict[str, Any],
) -> None:
    if name not in data:
        return
    section = data[name]
    _expect_table(config_path, name, section)
    for key, value in section.items():
        validator = validators.get(key)
        if validator is not None:
            validator(config_path, f"{name}.{key}", value)


def _validate_boundaries_section(data: dict[str, Any], config_path: Path | None) -> None:
    if "boundaries" not in data:
        return
    section = data["boundaries"]
    _expect_table(config_path, "boundaries", section)
    if "rules" not in section:
        return
    rules = section["rules"]
    if not isinstance(rules, list):
        _type_error(config_path, "boundaries.rules", "list of tables", rules)
    for index, raw in enumerate(rules):
        key_prefix = f"boundaries.rules[{index}]"
        _expect_table(config_path, key_prefix, raw)
        if "name" in raw:
            _expect_str(config_path, f"{key_prefix}.name", raw["name"])
        if "severity" in raw:
            _expect_str(config_path, f"{key_prefix}.severity", raw["severity"])
        if "from" in raw:
            _expect_str_or_str_list(config_path, f"{key_prefix}.from", raw["from"])
        if "from_patterns" in raw:
            _expect_str_or_str_list(config_path, f"{key_prefix}.from_patterns", raw["from_patterns"])
        if "disallow" in raw:
            _expect_str_or_str_list(config_path, f"{key_prefix}.disallow", raw["disallow"])


def _expect_table(config_path: Path | None, key: str, value: Any) -> None:
    if not isinstance(value, dict):
        _type_error(config_path, key, "table", value)


def _expect_bool(config_path: Path | None, key: str, value: Any) -> None:
    if not isinstance(value, bool):
        _type_error(config_path, key, "bool", value)


def _expect_int(config_path: Path | None, key: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        _type_error(config_path, key, "integer", value)


def _expect_str(config_path: Path | None, key: str, value: Any) -> None:
    if not isinstance(value, str):
        _type_error(config_path, key, "string", value)


def _expect_str_list(config_path: Path | None, key: str, value: Any) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _type_error(config_path, key, "list of strings", value)


def _expect_str_or_str_list(config_path: Path | None, key: str, value: Any) -> None:
    if isinstance(value, str):
        return
    _expect_str_list(config_path, key, value)


def _expect_str_dict(config_path: Path | None, key: str, value: Any) -> None:
    if not isinstance(value, dict):
        _type_error(config_path, key, "table of string values", value)
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            _type_error(config_path, f"{key}.{item_key}", "string", item_value)


def _type_error(config_path: Path | None, key: str, expected: str, value: Any) -> None:
    location = f"Config file {config_path}: " if config_path else "Config: "
    raise ConfigError(
        f"{location}field {key!r} expected {expected}, got {type(value).__name__}."
    )


def _validate(cfg: PythonConfig) -> None:
    for item in cfg.frameworks:
        if item not in {"auto", "django", "fastapi", "flask", "celery", "pytest", "click", "typer", "none"}:
            _config_error(cfg, "frameworks", f"Unsupported framework value: {item}")
    _validate_choice(
        cfg,
        "dead_code.confidence_for_init_exports",
        cfg.dead_code.confidence_for_init_exports,
        {"low", "medium", "high"},
    )
    if cfg.dupes.mode not in {"strict", "mild", "structural"}:
        _config_error(cfg, "dupes.mode", f"Unsupported duplicate mode: {cfg.dupes.mode}")
        cfg.dupes.mode = "mild"
    dupe_defaults = DupesConfig()
    for attr in ("min_lines", "min_tokens", "max_groups"):
        _validate_positive_int(cfg, f"dupes.{attr}", cfg.dupes, attr, getattr(dupe_defaults, attr))
    health_defaults = HealthConfig()
    for attr in (
        "max_cyclomatic",
        "max_cognitive",
        "max_function_lines",
        "max_file_lines",
        "hotspot_score_threshold",
    ):
        _validate_positive_int(cfg, f"health.{attr}", cfg.health, attr, getattr(health_defaults, attr))
    for rule in cfg.boundary_rules:
        if rule.severity not in {"info", "warning", "error"}:
            _config_error(
                cfg,
                f"boundaries.rules.{rule.name}.severity",
                f"Unsupported boundary severity: {rule.severity}",
            )
            rule.severity = "warning"
        if not rule.from_patterns:
            _config_error(cfg, f"boundaries.rules.{rule.name}.from", "Boundary rule has no from patterns.")
        if not rule.disallow:
            _config_error(cfg, f"boundaries.rules.{rule.name}.disallow", "Boundary rule has no disallow patterns.")


def _validate_choice(cfg: PythonConfig, key: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        _config_error(cfg, key, f"Unsupported value {value!r}; expected one of {sorted(allowed)}.")


def _validate_positive_int(cfg: PythonConfig, key: str, target: object, attr: str, default: int) -> None:
    value = getattr(target, attr)
    if not isinstance(value, int) or value <= 0:
        _config_error(cfg, key, f"Expected a positive integer, got {value!r}.")
        setattr(target, attr, default)


def _config_error(cfg: PythonConfig, key: str, message: str) -> None:
    cfg.config_errors.append({"key": key, "message": message})
