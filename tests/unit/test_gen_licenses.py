"""`scripts/gen_licenses.py` 的单元测试。

重点是失败路径：许可证策略违规和清单过期都必须让 CI 失败，否则门禁形同虚设。
真实的 pip-licenses 调用被替换掉，测试不依赖本机装了哪些包。
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from scripts import gen_licenses

if TYPE_CHECKING:
    from pathlib import Path

FAKE_TABLE = "| Name | Version | License | URL |\n|---|---|---|---|\n| rich | 15.0.0 | MIT | x |\n"
OFFENDER_LINE = "license GPL-3.0-only not in allow-only licenses was found for pkg:1.0.0"


def _completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def fake_piplicenses(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """按调用参数返回预设结果，并暴露可修改的状态。"""
    state: dict[str, object] = {"policy_ok": True, "table": FAKE_TABLE}

    def _fake(*args: str) -> subprocess.CompletedProcess[str]:
        if any(arg.startswith("--allow-only") for arg in args):
            if state["policy_ok"]:
                return _completed(0)
            return _completed(1, stdout=OFFENDER_LINE)
        return _completed(0, stdout=str(state["table"]))

    monkeypatch.setattr(gen_licenses, "_run_piplicenses", _fake)
    return state


@pytest.fixture
def output_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """把清单输出重定向到临时目录，避免改动仓库里的真实文件。"""
    target = tmp_path / "docs" / "THIRD_PARTY_LICENSES.md"
    monkeypatch.setattr(gen_licenses, "OUTPUT_PATH", target)
    return target


def test_generate_writes_header_and_table(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    assert gen_licenses.main([]) == 0

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# 第三方依赖许可证清单")
    assert "rich" in content
    assert content.endswith("\n")


def test_check_passes_on_fresh_manifest(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen_licenses.main([])
    capsys.readouterr()

    assert gen_licenses.main(["--check"]) == 0
    assert "许可证检查通过" in capsys.readouterr().out


def test_check_fails_when_manifest_is_stale(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen_licenses.main([])
    output_path.write_text("手工改过的旧内容\n", encoding="utf-8")
    capsys.readouterr()

    assert gen_licenses.main(["--check"]) == 1
    assert "清单已过期" in capsys.readouterr().err


def test_check_fails_when_manifest_is_missing(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not output_path.exists()

    assert gen_licenses.main(["--check"]) == 1
    assert "清单不存在" in capsys.readouterr().err


def test_check_fails_on_license_outside_whitelist(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen_licenses.main([])
    fake_piplicenses["policy_ok"] = False
    capsys.readouterr()

    assert gen_licenses.main(["--check"]) == 1
    err = capsys.readouterr().err
    assert "许可证策略检查失败" in err
    assert "GPL-3.0-only" in err
    assert "ALLOWED_LICENSES" in err


def test_policy_failure_short_circuits_before_writing(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    """策略违规时不写文件，避免把不合规的清单落盘。"""
    fake_piplicenses["policy_ok"] = False

    assert gen_licenses.main([]) == 1
    assert not output_path.exists()


def test_empty_table_is_rejected(fake_piplicenses: dict[str, object]) -> None:
    fake_piplicenses["table"] = "   "

    with pytest.raises(SystemExit, match="没有返回任何依赖"):
        gen_licenses.build_content()


def test_allowed_licenses_are_lowercase_free_and_semicolon_joined() -> None:
    """白名单参数必须是分号分隔的常量，防止有人塞进逗号导致静默失效。"""
    assert ";" in gen_licenses.ALLOWED_LICENSES_ARG
    assert "," not in gen_licenses.ALLOWED_LICENSES_ARG
    assert gen_licenses.ALLOWED_LICENSES_ARG.split(";") == list(gen_licenses.ALLOWED_LICENSES)
