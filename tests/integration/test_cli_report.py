"""``agent-doctor report`` 的端到端行为。"""

import json
from pathlib import Path

BUILTIN_CHECKS = {
    "python.version",
    "platform.info",
    "path.health",
    "toolchain.presence",
    "fs.health",
    "windows.longpath",
}


def test_report_defaults_to_json_on_stdout(run_cli) -> None:
    outcome = run_cli("report")
    assert outcome.exit_code == 0

    payload = json.loads(outcome.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["summary"]["total"] == len(payload["results"])
    assert {item["name"] for item in payload["results"]} == BUILTIN_CHECKS


def test_report_text_format(run_cli) -> None:
    outcome = run_cli("report", "--format", "text")
    assert outcome.exit_code == 0
    assert "诊断报告" in outcome.stdout
    assert "[PASS]" in outcome.stdout or "[WARN]" in outcome.stdout
    assert "python.version" in outcome.stdout


def test_report_writes_file(run_cli, tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    outcome = run_cli("report", "--output", str(target))
    assert outcome.exit_code == 0
    assert "已写入" in outcome.stdout

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["tool"]["name"] == "agent-doctor"


def test_report_refuses_to_overwrite_without_force(run_cli, tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("原始内容", encoding="utf-8")

    outcome = run_cli("report", "--output", str(target))
    assert outcome.exit_code == 2
    assert "--force" in outcome.text
    assert target.read_text(encoding="utf-8") == "原始内容"


def test_report_overwrites_with_force(run_cli, tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("原始内容", encoding="utf-8")

    outcome = run_cli("report", "--output", str(target), "--force")
    assert outcome.exit_code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "1.0"


def test_report_missing_output_directory(run_cli, tmp_path: Path) -> None:
    outcome = run_cli("report", "--output", str(tmp_path / "nope" / "report.json"))
    assert outcome.exit_code == 2
    assert "目录不存在" in outcome.text
    assert "Traceback" not in outcome.text


def test_report_invalid_format(run_cli) -> None:
    outcome = run_cli("report", "--format", "xml")
    assert outcome.exit_code == 2


def test_report_only_filters(run_cli) -> None:
    outcome = run_cli("report", "--only", "python.version")
    assert outcome.exit_code == 0

    payload = json.loads(outcome.stdout)
    assert len(payload["results"]) == 1
    assert payload["results"][0]["name"] == "python.version"
