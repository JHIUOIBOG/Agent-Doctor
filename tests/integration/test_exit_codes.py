"""全局行为：帮助、版本、退出码契约、不出现裸 traceback。"""

from pathlib import Path

import pytest


def test_help_lists_all_commands(run_cli) -> None:
    outcome = run_cli("--help")
    assert outcome.exit_code == 0
    for command in ("check", "proxy", "hash"):
        assert command in outcome.text


def test_version_flag(run_cli) -> None:
    outcome = run_cli("--version")
    assert outcome.exit_code == 0
    assert "agent-doctor" in outcome.text
    assert "0.1.0" in outcome.text


def test_unknown_command_returns_two(run_cli) -> None:
    outcome = run_cli("does-not-exist")
    assert outcome.exit_code == 2


def test_missing_required_option_returns_two(run_cli) -> None:
    outcome = run_cli("proxy")
    assert outcome.exit_code == 2


def test_missing_required_argument_returns_two(run_cli) -> None:
    outcome = run_cli("hash")
    assert outcome.exit_code == 2


@pytest.mark.parametrize(
    "args",
    [
        ("hash", "missing-file.bin"),
        ("hash", "."),
        ("proxy", "--port", "70000"),
        ("check", "--only", "nope"),
    ],
)
def test_failures_never_print_traceback(run_cli, args: tuple[str, ...]) -> None:
    outcome = run_cli(*args)
    assert outcome.exit_code == 2
    assert "Traceback" not in outcome.text


def test_error_message_goes_to_stderr_not_stdout(run_cli, tmp_path: Path) -> None:
    outcome = run_cli("hash", str(tmp_path / "missing.bin"))
    assert "不存在" in outcome.text
    # 成功路径的 stdout 必须是干净的结果，失败信息不应混进去
    assert "不存在" not in outcome.stdout


def test_unexpected_exception_returns_three(run_cli, monkeypatch) -> None:
    """兜底逻辑：内部异常不能变成裸 traceback，退出码必须是 3。"""

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("kaboom")

    monkeypatch.setattr("agent_doctor.cli.commands.check.run_checks", boom)
    outcome = run_cli("check")
    assert outcome.exit_code == 3
    assert "内部错误" in outcome.text
    assert "Traceback" not in outcome.text
