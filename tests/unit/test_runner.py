"""执行器：单个检查失败不影响整份报告。"""

from datetime import UTC, datetime

from agent_doctor.core.errors import PathError
from agent_doctor.core.registry import Check
from agent_doctor.core.runner import run_checks
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult


def _passing() -> CheckResult:
    return CheckResult(name="passing", status=Status.PASS, summary="正常")


def _unexpected() -> CheckResult:
    raise RuntimeError("kaboom")


def _domain_error() -> CheckResult:
    raise PathError("文件不存在：x")


def test_single_passing_check() -> None:
    report = run_checks([Check(name="passing", title="正常项", run=_passing)])
    assert report.summary.total == 1
    assert report.summary.passed == 1
    assert report.summary.failures == 0


def test_unexpected_exception_becomes_failure_result() -> None:
    report = run_checks(
        [
            Check(name="passing", title="正常项", run=_passing),
            Check(name="unexpected", title="坏项", run=_unexpected),
        ]
    )
    assert report.summary.total == 2
    assert report.summary.passed == 1
    assert report.summary.failures == 1

    failed = next(item for item in report.results if item.status is Status.FAIL)
    assert "RuntimeError" in failed.summary
    assert failed.recommendation


def test_domain_error_message_is_preserved() -> None:
    report = run_checks([Check(name="domain", title="业务错误", run=_domain_error)])
    result = report.results[0]
    assert result.status is Status.FAIL
    assert "文件不存在" in result.summary


def test_injected_timestamp_is_used() -> None:
    moment = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
    assert run_checks([], now=moment).generated_at == moment


def test_report_carries_tool_version() -> None:
    report = run_checks([Check(name="passing", title="正常项", run=_passing)])
    assert report.tool.name == "agent-doctor"
    assert report.tool.version
