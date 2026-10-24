"""版本探测服务：结果分类、版本号解析、子进程调用约束。"""

import subprocess

import pytest

from agent_doctor.services import versions
from agent_doctor.services.versions import (
    ProbeOutcome,
    parse_version,
    probe_all,
    probe_version,
)


class _RunSpy:
    """替身 subprocess.run，记录调用参数以便断言安全约束。"""

    def __init__(self, *, returncode: int = 0, stdout: str = "", exc: Exception | None = None):
        self.returncode = returncode
        self.stdout = stdout
        self.exc = exc
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append((cmd, kwargs))
        if self.exc is not None:
            raise self.exc
        return subprocess.CompletedProcess(cmd, self.returncode, self.stdout, "")


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> _RunSpy:
    """让 which 返回固定路径，并用 _RunSpy 接管 subprocess.run。"""
    fake = _RunSpy(stdout="git version 2.43.0.windows.1\n")
    monkeypatch.setattr(versions.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(versions.subprocess, "run", fake)
    return fake


# --- parse_version -------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("git version 2.43.0.windows.1\n", "2.43.0.windows.1"),
        ("v20.11.0\n", "20.11.0"),
        ("uv 0.1.24", "0.1.24"),
        ("10.2.4", "10.2.4"),
    ],
)
def test_parse_version_extracts_number(raw: str, expected: str) -> None:
    assert parse_version(raw) == expected


@pytest.mark.parametrize("raw", ["", "   \n", "no digits here", "version unknown"])
def test_parse_version_returns_none_without_number(raw: str) -> None:
    assert parse_version(raw) is None


def test_parse_version_only_looks_at_first_line() -> None:
    """部分工具会先打印警告行，此时不应把第二行的版本号当成版本。"""
    assert parse_version("warning: something\n2.0.0\n") is None


def test_parse_version_truncates_long_output() -> None:
    result = parse_version("1.0." + "9" * 200)
    assert result is not None
    assert len(result) <= versions.MAX_VERSION_LENGTH


# --- probe_version: 成功路径 --------------------------------------------


def test_probe_returns_version_on_success(spy: _RunSpy) -> None:
    probe = probe_version("git")
    assert probe.outcome is ProbeOutcome.OK
    assert probe.version == "2.43.0.windows.1"
    assert probe.ok is True


def test_probe_invokes_subprocess_with_safety_constraints(spy: _RunSpy) -> None:
    """这是"受控调用"的核心断言：固定参数、无 shell、有超时、不接 stdin。"""
    probe_version("git", timeout=2.5)

    assert len(spy.calls) == 1
    cmd, kwargs = spy.calls[0]
    assert cmd == ["/usr/bin/git", "--version"]
    assert kwargs["shell"] is False
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["timeout"] == 2.5
    assert kwargs["check"] is False


def test_probe_ok_but_without_version_number(spy: _RunSpy) -> None:
    spy.stdout = "built without version info\n"
    probe = probe_version("git")
    assert probe.outcome is ProbeOutcome.OK
    assert probe.version is None
    assert probe.detail == "输出中未找到版本号"


# --- probe_version: 失败路径 --------------------------------------------


def test_probe_missing_command_does_not_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """工具缺失时不应该尝试启动子进程。"""
    called = False

    def _boom(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True
        raise AssertionError("缺失工具时不应调用 subprocess")

    monkeypatch.setattr(versions.shutil, "which", lambda _name: None)
    monkeypatch.setattr(versions.subprocess, "run", _boom)

    probe = probe_version("git")
    assert probe.outcome is ProbeOutcome.NOT_FOUND
    assert probe.version is None
    assert called is False


def test_probe_nonzero_exit_is_failed(spy: _RunSpy) -> None:
    spy.returncode = 128
    probe = probe_version("git")
    assert probe.outcome is ProbeOutcome.FAILED
    assert probe.detail == "退出码 128"
    assert probe.ok is False


def test_probe_timeout(spy: _RunSpy) -> None:
    spy.exc = subprocess.TimeoutExpired(cmd=["git"], timeout=3.0)
    probe = probe_version("git", timeout=3.0)
    assert probe.outcome is ProbeOutcome.TIMEOUT
    assert "3" in (probe.detail or "")


def test_probe_oserror_does_not_leak_full_path(spy: _RunSpy) -> None:
    """OSError 文本可能含完整路径，报告里只保留类别与系统描述。"""
    spy.exc = PermissionError(13, "Access is denied")
    probe = probe_version("git")
    assert probe.outcome is ProbeOutcome.ERROR
    assert probe.detail == "PermissionError: Access is denied"
    assert "/usr/bin/git" not in (probe.detail or "")


def test_probe_oserror_without_strerror(spy: _RunSpy) -> None:
    spy.exc = OSError()
    probe = probe_version("git")
    assert probe.outcome is ProbeOutcome.ERROR
    assert "无法启动" in (probe.detail or "")


# --- probe_all -----------------------------------------------------------


def test_probe_all_keeps_order(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_which(name: str) -> str | None:
        return None if name == "uv" else f"/usr/bin/{name}"

    def _fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, f"{cmd[0]} version 1.2.3\n", "")

    monkeypatch.setattr(versions.shutil, "which", _fake_which)
    monkeypatch.setattr(versions.subprocess, "run", _fake_run)

    probes = probe_all(("git", "node", "uv"))
    assert [p.command for p in probes] == ["git", "node", "uv"]
    assert [p.outcome for p in probes] == [
        ProbeOutcome.OK,
        ProbeOutcome.OK,
        ProbeOutcome.NOT_FOUND,
    ]
