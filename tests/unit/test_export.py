"""JSON 导出：编码、字段、脱敏。"""

import json
from datetime import UTC, datetime
from pathlib import Path

from agent_doctor.models.enums import Status
from agent_doctor.models.report import DiagnosticReport, ToolInfo
from agent_doctor.models.result import CheckResult
from agent_doctor.report.json_exporter import dumps

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
