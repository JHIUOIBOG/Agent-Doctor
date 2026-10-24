"""``agent-doctor check``：运行基础环境检查。"""

import typer

from agent_doctor.cli import rendering
from agent_doctor.core.registry import select
from agent_doctor.core.runner import run_checks
from agent_doctor.report.json_exporter import dumps


def check_command(
    only: list[str] | None = typer.Option(None, "--only", help="只运行指定检查项，可重复使用"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON 报告"),
    probe_versions: bool = typer.Option(
        False,
        "--probe-tool-versions",
        help="显式启用外部程序版本探测（会执行 git/node/npm/uv --version）",
    ),
) -> None:
    """运行基础环境检查（只读，不修改任何系统配置）。"""
    with rendering.guard():
        selected = select(tuple(only) if only else None, probe_versions=probe_versions)
        report = run_checks(selected, probe_versions=probe_versions)
        if json_output:
            typer.echo(dumps(report), nl=False)
        else:
            rendering.render_check_report(report)
        raise typer.Exit(code=1 if report.summary.has_failures else 0)
