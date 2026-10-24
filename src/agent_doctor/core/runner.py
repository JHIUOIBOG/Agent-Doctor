"""检查执行器：把多个检查项跑成一份报告。

核心约定：**单个检查项失败不会中断整次诊断**。抛出的异常被翻译成一条
``status=fail`` 的结果，其余检查项照常执行。
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from agent_doctor import __version__
from agent_doctor.core.errors import AgentDoctorError
from agent_doctor.core.registry import Check, select
from agent_doctor.models.enums import Status
from agent_doctor.models.report import DiagnosticReport, ToolInfo
from agent_doctor.models.result import CheckResult

LOGGER = logging.getLogger(__name__)


def run_checks(
    checks: Sequence[Check] | None = None,
    *,
    now: datetime | None = None,
    probe_versions: bool = False,
) -> DiagnosticReport:
    """执行检查项并组装报告。

    :param checks: 要执行的检查项；``None`` 表示注册表里的全部
    :param now: 注入的时间，便于测试得到稳定输出
    :param probe_versions: 是否包含需要执行外部程序的检查项；默认 ``False``，
        保证默认路径零进程创建
    """
    selected = tuple(checks) if checks is not None else select(probe_versions=probe_versions)
    results = tuple(_execute(item) for item in selected)
    return DiagnosticReport(
        tool=ToolInfo(version=__version__),
        generated_at=now or datetime.now(UTC),
        results=results,
    )


def _execute(item: Check) -> CheckResult:
    try:
        return item.run()
    except AgentDoctorError as exc:
        LOGGER.debug("检查项 %s 返回业务错误：%s", item.name, exc.message)
        return _failure(item, f"检查失败：{exc.message}", "按提示修正后重新运行")
    except Exception as exc:
        LOGGER.exception("检查项 %s 抛出未预期异常", item.name)
        return _failure(
            item,
            f"检查未完成：{type(exc).__name__}",
            "这是工具自身的缺陷，请附上 --log-level debug 的输出提交 issue",
        )


def _failure(item: Check, summary: str, recommendation: str) -> CheckResult:
    return CheckResult(
        name=item.name,
        status=Status.FAIL,
        summary=summary,
        details={"error": summary},
        recommendation=recommendation,
    )
