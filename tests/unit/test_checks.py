"""内置检查项本身的行为（不经过 CLI）。"""

import os
import shutil
from types import SimpleNamespace

import pytest

import agent_doctor.checks.fs_health as fs_module
from agent_doctor.checks import longpath
from agent_doctor.checks.path_health import path_health
from agent_doctor.checks.platform_info import platform_info
from agent_doctor.checks.python_env import python_version
from agent_doctor.checks.toolchain import toolchain_presence
from agent_doctor.models.enums import Status

GIB = 1024**3


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


def _disk_usage(free: int, total: int = 500 * GIB) -> SimpleNamespace:
    return SimpleNamespace(total=total, used=total - free, free=free)


def test_fs_health_passes_with_space(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fs_module, "_temp_dir_writable", lambda: True)
    monkeypatch.setattr(fs_module.shutil, "disk_usage", lambda path: _disk_usage(400 * GIB))
    result = fs_module.fs_health()
    assert result.status is Status.PASS
    assert result.details["temp_writable"] is True
    assert result.details["free_gb"] == 400.0


def test_fs_health_warns_on_low_space(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fs_module, "_temp_dir_writable", lambda: True)
    monkeypatch.setattr(fs_module.shutil, "disk_usage", lambda path: _disk_usage(1 * GIB))
    result = fs_module.fs_health()
    assert result.status is Status.WARN
    assert "空间不足" in result.summary


def test_fs_health_fails_when_temp_not_writable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fs_module, "_temp_dir_writable", lambda: False)
    monkeypatch.setattr(fs_module.shutil, "disk_usage", lambda path: _disk_usage(400 * GIB))
    result = fs_module.fs_health()
    assert result.status is Status.FAIL
    assert "不可写" in result.summary


def test_fs_health_warns_when_disk_usage_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(path: object) -> None:
        raise OSError(5, "Access is denied")

    monkeypatch.setattr(fs_module, "_temp_dir_writable", lambda: True)
    monkeypatch.setattr(fs_module.shutil, "disk_usage", boom)
    result = fs_module.fs_health()
    assert result.status is Status.WARN
    assert "无法读取磁盘空间" in result.summary


def test_temp_dir_writable_is_true_on_this_machine() -> None:
    assert fs_module._temp_dir_writable() is True


def test_long_paths_passes_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(longpath, "_IS_WINDOWS", True)
    monkeypatch.setattr(longpath, "_read_long_paths_flag", lambda: 1)
    result = longpath.long_paths()
    assert result.status is Status.PASS
    assert result.details["long_paths_enabled"] is True


def test_long_paths_warns_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(longpath, "_IS_WINDOWS", True)
    monkeypatch.setattr(longpath, "_read_long_paths_flag", lambda: 0)
    result = longpath.long_paths()
    assert result.status is Status.WARN
    assert result.recommendation


def test_long_paths_warns_when_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(longpath, "_IS_WINDOWS", True)
    monkeypatch.setattr(longpath, "_read_long_paths_flag", lambda: None)
    result = longpath.long_paths()
    assert result.status is Status.WARN
    assert "无法读取" in result.summary


def test_long_paths_is_info_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(longpath, "_IS_WINDOWS", False)
    result = longpath.long_paths()
    assert result.status is Status.INFO
    assert result.details["is_windows"] is False
