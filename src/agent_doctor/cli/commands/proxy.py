"""``agent-doctor proxy``：TCP 端口连通性探测。"""

import typer

from agent_doctor.cli import rendering
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult
from agent_doctor.report.json_exporter import dumps
from agent_doctor.services.net import (
    DEFAULT_TIMEOUT,
    ProbeOutcome,
    ensure_target_allowed,
    probe_tcp,
)

_RECOMMENDATIONS: dict[ProbeOutcome, str] = {
    ProbeOutcome.REFUSED: "端口没有监听：确认服务已启动，或核对端口号",
    ProbeOutcome.TIMEOUT: "超时通常是防火墙丢包或服务无响应；可尝试加大 --timeout",
    ProbeOutcome.DNS_ERROR: "主机名无法解析：检查拼写或 DNS 配置",
    ProbeOutcome.UNREACHABLE: "网络不可达：检查网卡、代理设置或目标地址",
}


def evaluate(host: str, port: int, timeout: float, *, allow_non_loopback: bool) -> CheckResult:
    """探测端口并组装结果。

    :raises UsageError: 主机/端口/超时参数不合法
    :raises NetworkError: 目标不是回环地址且未显式放行
    """
    ensure_target_allowed(host, allow_non_loopback=allow_non_loopback)
    probe = probe_tcp(host, port, timeout=timeout)

    details: dict[str, str | int | float | bool | None] = {
        "host": probe.host,
        "port": probe.port,
        "outcome": str(probe.outcome),
        "latency_ms": probe.latency_ms,
    }

    if probe.connected:
        return CheckResult(
            name="proxy.tcp",
            status=Status.PASS,
            summary=f"{probe.host}:{probe.port} 连接成功（{probe.latency_ms} ms）",
            details=details,
        )

    return CheckResult(
        name="proxy.tcp",
        status=Status.FAIL,
        summary=f"{probe.host}:{probe.port} 连接失败：{probe.detail}",
        details=details,
        recommendation=_RECOMMENDATIONS.get(probe.outcome),
    )


def proxy_command(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="目标主机（默认回环地址）"),
    port: int = typer.Option(..., "--port", "-p", help="目标端口（1-65535）"),
    timeout: float = typer.Option(DEFAULT_TIMEOUT, "--timeout", "-t", help="连接超时秒数（0-60）"),
    allow_non_loopback: bool = typer.Option(
        False,
        "--allow-non-loopback",
        help="允许探测非回环地址（默认只探测本机）",
    ),
    json_output: bool = typer.Option(False, "--json", help="以 JSON 输出结果"),
) -> None:
    """检查 host:port 的 TCP 连通性，只做握手，不发送应用层数据。"""
    with rendering.guard():
        result = evaluate(host, port, timeout, allow_non_loopback=allow_non_loopback)
        if json_output:
            typer.echo(dumps(result), nl=False)
        else:
            rendering.render_result(result)
        raise typer.Exit(code=result.exit_code)
