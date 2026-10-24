"""报告格式的契约测试。

这一层不关心检查项跑得对不对，只关心**导出的 JSON 结构不会悄悄变**：

- ``golden/report.json`` 是字节级快照，任何字段增删改都会让它失配；
- 字段级断言把每一层允许出现的键钉死；
- 状态取值和 ``schema_version`` 也一并钉死。

快照由固定输入生成（假数据 + 冻结时间），因此与运行环境无关，Windows 和 Linux 上结果一致。
修改报告结构时必须同步更新 ``golden/report.json`` 和 ``docs/REPORT_SCHEMA.md``，
并且提升 ``schema_version``——这是破坏性变更，不能靠"改一下快照"蒙混过去。
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from agent_doctor import __version__
from agent_doctor.models.enums import Status
from agent_doctor.models.report import DiagnosticReport, ToolInfo
from agent_doctor.models.result import CheckResult
from agent_doctor.report.json_exporter import dumps

GOLDEN_PATH = Path(__file__).parent / "golden" / "report.json"
FROZEN_NOW = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)

TOP_LEVEL_KEYS = {"schema_version", "tool", "generated_at", "results", "summary"}
TOOL_KEYS = {"name", "version"}
RESULT_KEYS = {"name", "status", "summary", "details", "recommendation"}
SUMMARY_KEYS = {"total", "passed", "warnings", "failures", "info"}
ALLOWED_STATUS = {"pass", "warn", "fail", "info"}
ALLOWED_DETAIL_TYPES = (str, bool, int, float, type(None))


def build_report() -> DiagnosticReport:
    """固定的示例报告：三种状态各一条，覆盖 details 的各种标量类型。"""
    return DiagnosticReport(
        tool=ToolInfo(version="0.1.0"),
        generated_at=FROZEN_NOW,
        results=(
            CheckResult(
                name="python.version",
                status=Status.PASS,
                summary="Python 3.12.7",
                details={"version": "3.12.7", "in_virtualenv": True, "minor": 12, "ratio": 1.5},
            ),
            CheckResult(
                name="path.health",
                status=Status.WARN,
                summary="PATH 共 41 项：2 个目录不存在",
                details={"entries": 41, "missing": 2, "duplicated": 0},
                recommendation="在系统环境变量里手动清理无效条目",
            ),
            CheckResult(
                name="fs.health",
                status=Status.FAIL,
                summary="临时目录不可写",
                details={"temp_writable": False, "free_gb": None},
                recommendation="检查 TEMP 目录权限",
            ),
        ),
    )


def test_export_matches_golden_file() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8")
    assert dumps(build_report()) == expected


def test_golden_file_is_valid_json() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"


def test_top_level_keys_are_fixed() -> None:
    payload = json.loads(dumps(build_report()))
    assert set(payload) == TOP_LEVEL_KEYS


def test_tool_block_keys_are_fixed() -> None:
    payload = json.loads(dumps(build_report()))
    assert set(payload["tool"]) == TOOL_KEYS
    assert payload["tool"]["name"] == "agent-doctor"


def test_result_keys_are_fixed() -> None:
    payload = json.loads(dumps(build_report()))
    for result in payload["results"]:
        assert set(result) == RESULT_KEYS


def test_summary_keys_are_fixed() -> None:
    payload = json.loads(dumps(build_report()))
    assert set(payload["summary"]) == SUMMARY_KEYS


def test_summary_counts_match_results() -> None:
    payload = json.loads(dumps(build_report()))
    statuses = [result["status"] for result in payload["results"]]
    assert payload["summary"]["total"] == len(statuses)
    assert payload["summary"]["passed"] == statuses.count("pass")
    assert payload["summary"]["warnings"] == statuses.count("warn")
    assert payload["summary"]["failures"] == statuses.count("fail")
    assert payload["summary"]["info"] == statuses.count("info")


def test_status_values_are_limited_to_four() -> None:
    payload = json.loads(dumps(build_report()))
    assert {result["status"] for result in payload["results"]} <= ALLOWED_STATUS


def test_details_values_are_flat_scalars() -> None:
    payload = json.loads(dumps(build_report()))
    for result in payload["results"]:
        for key, value in result["details"].items():
            assert isinstance(key, str)
            assert isinstance(value, ALLOWED_DETAIL_TYPES), f"{key} 的值类型不允许：{type(value)}"


def test_generated_at_is_utc_iso8601() -> None:
    payload = json.loads(dumps(build_report()))
    assert payload["generated_at"].endswith("Z")
    parsed = datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == FROZEN_NOW.utcoffset()


def test_tool_version_comes_from_package_version() -> None:
    """真实管道必须带上包版本，而不是写死字符串。"""
    from agent_doctor.core.runner import run_checks

    assert run_checks([]).tool.version == __version__
