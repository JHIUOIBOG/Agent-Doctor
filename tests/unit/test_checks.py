"""内置检查项本身的行为（不经过 CLI）。"""

import os
import shutil

import pytest

from agent_doctor.checks.path_health import path_health
from agent_doctor.checks.platform_info import platform_info
from agent_doctor.checks.python_env import python_version
from agent_doctor.checks.toolchain import toolchain_presence
from agent_doctor.models.enums import Status


def test_python_version_reports_current_interpreter() -> None:
    result = python_version()
    assert result.name == "python.version"
    assert result.status is Status.PASS
    assert result.details["version"].count(".") == 2
    assert isinstance(result.details["in_virtualenv"], bool)


def test_platform_info_returns_known_status() -> None:
    result = platform_info()
    assert result.name == "platform.info"
    assert result.status in {Status.PASS, Status.WARN, Status.INFO}
    assert "system" in result.details


def test_path_health_passes_on_clean_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    result = path_health()
    assert result.status is Status.PASS
    assert result.details["entries"] == 1
    assert result.details["missing"] == 0


def test_path_health_warns_on_missing_entry(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    missing = tmp_path / "definitely-not-here"
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path), str(missing)]))
    result = path_health()
    assert result.status is Status.WARN
    assert result.details["missing"] == 1
    assert "不存在" in result.summary
    assert result.recommendation


def test_path_health_warns_on_duplicates(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path), str(tmp_path)]))
    result = path_health()
    assert result.details["duplicated"] == 1


def test_path_health_fails_on_empty_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    result = path_health()
    assert result.status is Status.FAIL
    assert result.details["entries"] == 0


def test_toolchain_passes_when_everything_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: f"/fake/bin/{command}")
    result = toolchain_presence()
    assert result.status is Status.PASS
    assert result.recommendation is None


def test_toolchain_warns_when_everything_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)
    result = toolchain_presence()
    assert result.status is Status.WARN
    assert "Git" in result.summary
    assert result.recommendation
