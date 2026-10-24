"""终端渲染与错误兜底。

所有用户可见的输出都从这里出，命令函数只负责"算结果"。
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import typer
from rich.console import Console
from rich.table import Table

from agent_doctor.core.errors import AgentDoctorError
from agent_doctor.models.enums import Status
from agent_doctor.models.report import DiagnosticReport
from agent_doctor.models.result import CheckResult

LOGGER = logging.getLogger(__name__)

_STATUS_STYLE: dict[Status, str] = {
    Status.PASS: "green",
    Status.WARN: "yellow",
    Status.FAIL: "red",
    Status.INFO: "cyan",
}
_STATUS_LABEL: dict[Status, str] = {
    Status.PASS: "PASS",
    Status.WARN: "WARN",
    Status.FAIL: "FAIL",
    Status.INFO: "INFO",
}


def console() -> Console:
    """标准输出。非 TTY 时 Rich 会自动去掉颜色和动态效果。"""
    return Console(highlight=False, emoji=False)


def error_console() -> Console:
    """错误输出，永远走 stderr，避免污染管道里的 JSON。"""
    return Console(stderr=True, highlight=False, emoji=False)


def print_error(message: str) -> None:
    error_console().print(f"[bold red]错误[/bold red] {message}", soft_wrap=True)


@contextmanager
def guard() -> Iterator[None]:
    """把领域异常翻译成退出码，兜住未预期异常，保证不出现裸 traceback。"""
    try:
        yield
    except AgentDoctorError as exc:
        print_error(exc.message)
        raise typer.Exit(code=exc.exit_code) from None
    except typer.Exit:
        raise
    except Exception as exc:  # 最后一道兜底：任何未预期异常都不能变成裸 traceback
        # 默认只留一行摘要；完整堆栈要显式开 --log-level debug 才输出
        LOGGER.error("未处理的异常：%s: %s", type(exc).__name__, exc)
        LOGGER.debug("详细堆栈", exc_info=True)
        print_error(f"内部错误：{type(exc).__name__}（用 --log-level debug 查看详情）")
        raise typer.Exit(code=3) from None


def render_result(result: CheckResult) -> None:
    """渲染单条结果（hash / proxy 用）。"""
    out = console()
    style = _STATUS_STYLE[result.status]
    label = _STATUS_LABEL[result.status]
    out.print(f"[{style}]{label}[/{style}] {result.summary}")
    for key, value in result.details.items():
        out.print(f"  {key}: {value}")
    if result.recommendation:
        out.print(f"  建议: {result.recommendation}")


def render_check_report(report: DiagnosticReport) -> None:
    """渲染 ``check`` 的表格报告。"""
    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        show_edge=False,
        pad_edge=False,
    )
    table.add_column("状态", no_wrap=True)
    table.add_column("检查项", no_wrap=True)
    table.add_column("说明", overflow="fold")
    table.add_column("建议", overflow="fold")

    for result in report.results:
        style = _STATUS_STYLE[result.status]
        table.add_row(
            f"[{style}]{_STATUS_LABEL[result.status]}[/{style}]",
            result.name,
            result.summary,
            result.recommendation or "",
        )

    out = console()
    out.print(table)
    summary = report.summary
    out.print(
        f"共 {summary.total} 项：{summary.passed} 通过，"
        f"{summary.warnings} 警告，{summary.failures} 失败，{summary.info} 提示"
    )
