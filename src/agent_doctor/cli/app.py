"""Typer 应用装配。

这里只做三件事：注册子命令、处理全局选项、把日志初始化好。
业务逻辑一律不在这个文件里。
"""

import typer

import agent_doctor.checks  # noqa: F401  导入即注册内置检查项
from agent_doctor import __version__
from agent_doctor.cli.commands.check import check_command
from agent_doctor.cli.commands.hash import hash_command
from agent_doctor.cli.commands.proxy import proxy_command
from agent_doctor.logging_setup import configure_logging

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="本地 AI 编程环境诊断工具：只读、离线、不自动修复。",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agent-doctor {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="显示版本并退出",
    ),
    log_level: str = typer.Option(
        "WARNING", "--log-level", help="日志级别：DEBUG/INFO/WARNING/ERROR"
    ),
) -> None:
    """本地 AI 编程环境诊断工具。"""
    configure_logging(log_level)


app.command("check", help="运行基础环境检查")(check_command)
app.command("proxy", help="检查本地端口的 TCP 连通性")(proxy_command)
app.command("hash", help="计算文件 SHA-256")(hash_command)


def main() -> None:
    """控制台入口（``agent-doctor`` 命令）。"""
    app()
