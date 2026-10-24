"""TCP 端口连通性探测。

只做 TCP 三次握手，握手成功后立即关闭连接，**不发送任何应用层数据**。
这样既能判断端口是否可用，又不会向目标服务投递半截请求。

默认策略是"只允许回环地址"，探测外部主机必须由调用方显式放行，
避免这个工具被当成端口扫描器使用。
"""

import errno
import ipaddress
import socket
import time
from dataclasses import dataclass
from enum import StrEnum

from agent_doctor.core.errors import NetworkError, UsageError

DEFAULT_TIMEOUT = 3.0
MAX_TIMEOUT = 60.0

#: Windows 上 connect 的 winerror 取值
_WINERROR_TIMEOUT = 10060
_WINERROR_REFUSED = 10061
_WINERROR_UNREACHABLE = frozenset({10051, 10065})


class ProbeOutcome(StrEnum):
    """一次探测的分类结果。"""

    CONNECTED = "connected"
    REFUSED = "refused"
    TIMEOUT = "timeout"
    DNS_ERROR = "dns_error"
    UNREACHABLE = "unreachable"


@dataclass(frozen=True, slots=True)
class PortProbe:
    """一次探测的完整结果。"""

    host: str
    port: int
    outcome: ProbeOutcome
    latency_ms: float | None = None
    detail: str | None = None

    @property
    def connected(self) -> bool:
        return self.outcome is ProbeOutcome.CONNECTED


def validate_port(port: int) -> int:
    """校验端口范围。"""
    if isinstance(port, bool) or not isinstance(port, int):
        raise UsageError("端口必须是整数")
    if not 1 <= port <= 65535:
        raise UsageError(f"端口必须在 1-65535 之间，收到 {port}")
    return port


def validate_timeout(timeout: float) -> float:
    """校验超时秒数。"""
    if timeout <= 0:
        raise UsageError("--timeout 必须大于 0 秒")
    if timeout > MAX_TIMEOUT:
        raise UsageError(f"--timeout 不要超过 {MAX_TIMEOUT:.0f} 秒")
    return timeout


def validate_host(host: str) -> str:
    """校验主机参数。

    刻意拒绝 URL 形式：``--host http://user:pass@host`` 会让凭据进入命令行历史、
    错误信息和报告，而这三处都不该出现密码。
    """
    target = host.strip()
    if not target:
        raise UsageError("--host 不能为空")
    if "://" in target or "@" in target:
        raise UsageError("--host 只接受主机名或 IP，不要传完整 URL（避免凭据进入输出）")
    return target


def is_loopback(host: str) -> bool:
    """判断主机是否是回环地址（含 ``localhost``、``::1``）。"""
    candidate = host.strip().strip("[]").lower()
    if candidate == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def ensure_target_allowed(host: str, *, allow_non_loopback: bool) -> None:
    """非回环地址需要显式放行。"""
    target = validate_host(host)
    if allow_non_loopback or is_loopback(target):
        return
    raise NetworkError(
        f"{target} 不是回环地址。本工具默认只探测本机端口；"
        "确认要探测外部主机请显式加 --allow-non-loopback"
    )


def probe_tcp(host: str, port: int, *, timeout: float = DEFAULT_TIMEOUT) -> PortProbe:
    """探测 ``host:port`` 的 TCP 连通性。

    :raises UsageError: 主机或端口参数不合法
    """
    target = validate_host(host)
    validate_port(port)
    validate_timeout(timeout)

    started = time.perf_counter()
    try:
        with socket.create_connection((target, port), timeout=timeout):
            pass
    except ConnectionRefusedError:
        return _build(target, port, ProbeOutcome.REFUSED, started, "目标端口拒绝连接（端口未监听）")
    except TimeoutError:
        return _build(target, port, ProbeOutcome.TIMEOUT, started, f"连接超时（{timeout:g} 秒）")
    except socket.gaierror:
        return _build(target, port, ProbeOutcome.DNS_ERROR, started, "无法解析主机名")
    except OSError as exc:
        return _build(target, port, _classify_os_error(exc), started, _describe(exc))
    return _build(target, port, ProbeOutcome.CONNECTED, started, None)


def _build(
    host: str,
    port: int,
    outcome: ProbeOutcome,
    started: float,
    detail: str | None,
) -> PortProbe:
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return PortProbe(host=host, port=port, outcome=outcome, latency_ms=elapsed_ms, detail=detail)


def _classify_os_error(exc: OSError) -> ProbeOutcome:
    winerror = getattr(exc, "winerror", None)
    if winerror == _WINERROR_TIMEOUT or exc.errno == errno.ETIMEDOUT:
        return ProbeOutcome.TIMEOUT
    if winerror == _WINERROR_REFUSED or exc.errno == errno.ECONNREFUSED:
        return ProbeOutcome.REFUSED
    if winerror in _WINERROR_UNREACHABLE:
        return ProbeOutcome.UNREACHABLE
    if exc.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH):
        return ProbeOutcome.UNREACHABLE
    return ProbeOutcome.UNREACHABLE


def _describe(exc: OSError) -> str:
    reason = exc.strerror or str(exc)
    return f"连接失败：{reason}"
