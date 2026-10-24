"""``agent-doctor report``：导出结构化诊断报告。"""

from enum import StrEnum

import typer

from agent_doctor.cli import rendering
from agent_doctor.core.registry import select
from agent_doctor.core.runner import run_checks
from agent_doctor.models.report import DiagnosticReport
from agent_doctor.report.json_exporter import dumps
from agent_doctor.report.text_exporter import render_text
from agent_doctor.report.writer import write_text_atomic
from agent_doctor.security.paths import normalize_path


class ReportFormat(StrEnum):
    """报告输出格式。"""

    JSON = "json"
    TEXT = "text"


def build_report_text(report: DiagnosticReport, output_format: ReportFormat) -> str:
    """按格式渲染报告文本（两种格式都会脱敏）。"""
    if output_format is ReportFormat.TEXT:
        return render_text(report)
    return dumps(report)


def report_command(
    output_format: ReportFormat = typer.Option(
        ReportFormat.JSON, "--format", "-f", help="输出格式"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="写入文件而不是标准输出"),
    force: bool = typer.Option(False, "--force", help="允许覆盖已存在的输出文件"),
    only: list[str] | None = typer.Option(None, "--only", help="只运行指定检查项，可重复使用"),
    probe_versions: bool = typer.Option(
        False,
        "--probe-tool-versions",
        help="显式启用外部程序版本探测（会执行 git/node/npm/uv --version）",
    ),
) -> None:
    """导出结构化诊断报告（只读，不修改任何系统配置）。"""
    with rendering.guard():
        selected = select(tuple(only) if only else None, probe_versions=probe_versions)
        report = run_checks(selected, probe_versions=probe_versions)
        text = build_report_text(report, output_format)
        if output is None:
            typer.echo(text, nl=False)
        else:
            target = write_text_atomic(text, normalize_path(output), force=force)
            typer.echo(f"已写入 {target}")
        raise typer.Exit(code=0)
