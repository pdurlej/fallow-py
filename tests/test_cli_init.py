from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 15


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def test_init_dry_run() -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    res = subprocess.run(
        [sys.executable, "-m", "fallow_py", "init", "--dry-run"],
        text=True,
        capture_output=True,
        env=env,
        timeout=TIMEOUT,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "[tool.fallow_py]" in res.stdout
    assert 'roots = ["src"]' in res.stdout
    assert 'entry = ["src/app/main.py"]' in res.stdout


def test_init_write(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    res = subprocess.run(
        [sys.executable, "-m", "fallow_py", "init", "--write", "--root", str(tmp_path)],
        text=True,
        capture_output=True,
        env=env,
        timeout=TIMEOUT,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Created fallow-py configuration at .fallow-py.toml" in res.stdout

    written_config = tmp_path / ".fallow-py.toml"
    assert written_config.exists()

    doctor = subprocess.run(
        [sys.executable, "-m", "fallow_py", "doctor", "--root", str(tmp_path)],
        text=True,
        capture_output=True,
        env=env,
        timeout=TIMEOUT,
    )
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "Config: .fallow-py.toml" in doctor.stdout

    res2 = subprocess.run(
        [sys.executable, "-m", "fallow_py", "init", "--write", "--root", str(tmp_path)],
        text=True,
        capture_output=True,
        env=env,
        timeout=TIMEOUT,
    )
    assert res2.returncode != 0
    assert "Config file already exists" in res2.stderr

    tmp_path2 = tmp_path / "candidate_test"
    tmp_path2.mkdir()
    (tmp_path2 / ".fallow.toml").write_text("", encoding="utf-8")
    res3 = subprocess.run(
        [sys.executable, "-m", "fallow_py", "init", "--write", "--root", str(tmp_path2)],
        text=True,
        capture_output=True,
        env=env,
        timeout=TIMEOUT,
    )
    assert res3.returncode != 0
    assert "Config file already exists: .fallow.toml" in res3.stderr

    tmp_path3 = tmp_path / "pyproject_test"
    tmp_path3.mkdir()
    write(
        tmp_path3 / "pyproject.toml",
        """
        [tool.fallow_py]
        some_setting = true
        """,
    )
    res4 = subprocess.run(
        [sys.executable, "-m", "fallow_py", "init", "--write", "--root", str(tmp_path3)],
        text=True,
        capture_output=True,
        env=env,
        timeout=TIMEOUT,
    )
    assert res4.returncode != 0
    assert "Config already exists in pyproject.toml" in res4.stderr
