"""聚合报告与汇总计数。"""

from datetime import UTC, datetime

from agent_doctor.models.enums import Status
from agent_doctor.models.report import DiagnosticReport, ToolInfo
from agent_doctor.models.result import CheckResult

MOMENT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


def _report(*statuses: Status) -> DiagnosticReport:
    results = tuple(
        CheckResult(name=f"check.{index}", status=status, summary="s")
        for index, status in enumerate(statuses)
    )
    return DiagnosticReport(tool=ToolInfo(version="0.1.0"), generated_at=MOMENT, results=results)


def test_summary_counts_each_status() -> None:
    report = _report(Status.PASS, Status.PASS, Status.WARN, Status.FAIL, Status.INFO)
    assert report.summary.total == 5
    assert report.summary.passed == 2
    assert report.summary.warnings == 1
    assert report.summary.failures == 1
    assert report.summary.info == 1
    assert report.summary.has_failures is True


def test_summary_without_failures() -> None:
    assert _report(Status.PASS, Status.INFO).summary.has_failures is False


def test_summary_is_serialized() -> None:
    payload = _report(Status.PASS).model_dump(mode="json")
    assert payload["schema_version"] == "1.0"
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["failures"] == 0
    assert payload["tool"]["name"] == "agent-doctor"


def test_empty_report_is_valid() -> None:
    report = _report()
    assert report.summary.total == 0
    assert report.summary.has_failures is False
