"""JSON 导出：编码、字段、脱敏。"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_doctor.core.errors import PathError, UsageError
from agent_doctor.models.enums import Status
from agent_doctor.models.report import DiagnosticReport, ToolInfo
from agent_doctor.models.result import CheckResult
from agent_doctor.report.json_exporter import dumps
from agent_doctor.report.text_exporter import render_text
from agent_doctor.report.writer import write_text_atomic

MOMENT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


def test_chinese_is_not_escaped() -> None:
    result = CheckResult(name="demo", status=Status.PASS, summary="中文说明")
    text = dumps(result)
    assert "中文说明" in text
    assert "\\u" not in text


def test_report_json_has_expected_shape() -> None:
    report = DiagnosticReport(
        tool=ToolInfo(version="0.1.0"),
        generated_at=MOMENT,
        results=(CheckResult(name="demo", status=Status.PASS, summary="s"),),
    )
    payload = json.loads(dumps(report))
    assert payload["schema_version"] == "1.0"
    assert payload["tool"] == {"name": "agent-doctor", "version": "0.1.0"}
    assert payload["summary"]["total"] == 1
    assert payload["results"][0]["status"] == "pass"
    assert payload["generated_at"].startswith("2026-10-24T09:00:00")


def test_home_path_is_redacted_in_output() -> None:
    home = Path.home()
    result = CheckResult(
        name="file.hash",
        status=Status.PASS,
        summary="ok",
        details={"path": str(home / "a.txt")},
    )
    payload = json.loads(dumps(result))
    assert str(home) not in payload["details"]["path"]
    assert payload["details"]["path"].startswith("<")


def test_secrets_are_redacted_in_output() -> None:
    result = CheckResult(
        name="demo",
        status=Status.WARN,
        summary="key sk-abcdefghijklmnop leaked",
        details={"token": "ghp_" + "a" * 20},
    )
    payload = json.loads(dumps(result))
    assert "sk-abcdefghijklmnop" not in payload["summary"]
    assert "ghp_" not in payload["details"]["token"]


def test_output_ends_with_single_newline() -> None:
    text = dumps(CheckResult(name="demo", status=Status.PASS, summary="s"))
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def _sample_report() -> DiagnosticReport:
    return DiagnosticReport(
        tool=ToolInfo(version="0.1.0"),
        generated_at=MOMENT,
        results=(
            CheckResult(name="python.version", status=Status.PASS, summary="Python 3.12.7"),
            CheckResult(
                name="path.health",
                status=Status.WARN,
                summary="PATH 有 2 个目录不存在",
                recommendation="手动清理无效条目",
            ),
        ),
    )


def test_text_export_contains_statuses_and_summary() -> None:
    text = render_text(_sample_report())
    assert "诊断报告" in text
    assert "[PASS] python.version" in text
    assert "[WARN] path.health" in text
    assert "建议: 手动清理无效条目" in text
    assert "共 2 项：1 通过，1 警告，0 失败，0 提示" in text
    assert text.endswith("\n")


def test_text_export_is_plain_text() -> None:
    text = render_text(_sample_report())
    assert "\x1b[" not in text


def test_text_export_redacts_paths() -> None:
    report = DiagnosticReport(
        tool=ToolInfo(version="0.1.0"),
        generated_at=MOMENT,
        results=(
            CheckResult(
                name="file.hash",
                status=Status.PASS,
                summary=f"已读取 {Path.home() / 'secret.txt'}",
            ),
        ),
    )
    text = render_text(report)
    assert str(Path.home()) not in text
    assert "<HOME>" in text


def test_writer_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    assert write_text_atomic('{"a": 1}\n', target) == target
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n'


def test_writer_refuses_overwrite_without_force(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(UsageError):
        write_text_atomic("new", target)
    assert target.read_text(encoding="utf-8") == "old"


def test_writer_overwrites_with_force(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("old", encoding="utf-8")

    write_text_atomic("new", target, force=True)
    assert target.read_text(encoding="utf-8") == "new"


def test_writer_requires_existing_parent(tmp_path: Path) -> None:
    with pytest.raises(PathError) as excinfo:
        write_text_atomic("x", tmp_path / "nope" / "report.json")
    assert "目录不存在" in excinfo.value.message


def test_writer_rejects_directory_target(tmp_path: Path) -> None:
    with pytest.raises(PathError) as excinfo:
        write_text_atomic("x", tmp_path)
    assert "目录" in excinfo.value.message


def test_writer_leaves_no_temp_files(tmp_path: Path) -> None:
    write_text_atomic("x", tmp_path / "report.json")
    assert list(tmp_path.glob(".agent-doctor-*")) == []
