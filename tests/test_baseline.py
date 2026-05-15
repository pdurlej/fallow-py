from __future__ import annotations

import json

import pytest

from fallow_py.baseline import read_baseline
from fallow_py.config import ConfigError


def test_read_baseline_rejects_integer_issue_fingerprints(tmp_path) -> None:
    path = tmp_path / "bad-baseline.json"
    path.write_text(
        json.dumps({"version": "1.0", "issues": [{"fingerprint": 12345}, {"fingerprint": 67890}]}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as exc_info:
        read_baseline(path)

    message = str(exc_info.value)
    assert "issues" in message
    assert "fingerprint" in message
    assert "indices [0, 1]" in message


def test_read_baseline_rejects_integer_legacy_fingerprints(tmp_path) -> None:
    path = tmp_path / "bad-legacy-baseline.json"
    path.write_text(json.dumps({"version": "1.0", "fingerprints": [12345, 67890]}), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        read_baseline(path)

    assert "fingerprints" in str(exc_info.value)
    assert "indices [0, 1]" in str(exc_info.value)


def test_read_baseline_rejects_missing_version(tmp_path) -> None:
    path = tmp_path / "no-version.json"
    path.write_text(json.dumps({"issues": [{"fingerprint": "abc"}]}), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        read_baseline(path)

    assert "version" in str(exc_info.value)


def test_read_baseline_rejects_non_object_top_level(tmp_path) -> None:
    path = tmp_path / "list.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        read_baseline(path)

    assert "JSON object at top level" in str(exc_info.value)


def test_read_baseline_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        read_baseline(path)

    assert "not valid JSON" in str(exc_info.value)


def test_read_baseline_accepts_valid_baseline(tmp_path) -> None:
    path = tmp_path / "good.json"
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "issues": [{"fingerprint": "abc123"}, {"fingerprint": "def456"}],
            }
        ),
        encoding="utf-8",
    )

    data = read_baseline(path)

    assert data["version"] == "1.0"
    assert [item["fingerprint"] for item in data["issues"]] == ["abc123", "def456"]
