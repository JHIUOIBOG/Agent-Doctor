"""TCP 探测：真实监听端口、关闭端口、超时、DNS、参数校验。"""

from __future__ import annotations

import socket

import pytest

from agent_doctor.core.errors import NetworkError, UsageError
from agent_doctor.services import net
from agent_doctor.services.net import ProbeOutcome, is_loopback, probe_tcp, validate_port


class FakeSocket:
    """替身：记录是否被 with 语句正确关闭。"""

    def __init__(self) -> None:
        self.exited = False

    def __enter__(self) -> FakeSocket:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self.exited = True
        return False


def test_connects_to_local_listener(listener) -> None:
    probe = probe_tcp("127.0.0.1", listener.port, timeout=2.0)
    assert probe.outcome is ProbeOutcome.CONNECTED
    assert probe.connected is True
    assert probe.latency_ms is not None
    assert probe.latency_ms >= 0


def test_no_payload_is_sent(listener) -> None:
    probe_tcp("127.0.0.1", listener.port, timeout=2.0)
    listener.wait()
    # 握手完成后客户端立刻关闭，服务端 recv 只能拿到 EOF（b""），不会收到任何字节
    assert listener.received == [b""]


def test_socket_is_closed_after_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSocket()
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: fake)
    probe = probe_tcp("127.0.0.1", 65000, timeout=0.1)
    assert probe.outcome is ProbeOutcome.CONNECTED
    assert fake.exited is True


def test_connection_refused_is_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise ConnectionRefusedError(61, "Connection refused")

    monkeypatch.setattr(socket, "create_connection", boom)
    probe = probe_tcp("127.0.0.1", 65000, timeout=0.5)
    assert probe.outcome is ProbeOutcome.REFUSED


def test_closed_port_is_not_connected(free_port: int) -> None:
    """真实关闭的端口必须判为"未连通"。

    注意：本机（Windows + 防火墙）对关闭端口的 SYN 是丢弃而非回 RST，
    实测拿到的是 timeout；在没有防火墙拦截的环境会是 refused。两者都算失败。
    """
    probe = probe_tcp("127.0.0.1", free_port, timeout=1.0)
    assert probe.connected is False
    assert probe.outcome in {ProbeOutcome.REFUSED, ProbeOutcome.TIMEOUT}
    assert probe.detail is not None


def test_timeout_is_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", boom)
    probe = probe_tcp("127.0.0.1", 65000, timeout=0.5)
    assert probe.outcome is ProbeOutcome.TIMEOUT


def test_dns_error_is_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise socket.gaierror(-2, "Name or service not known")

    monkeypatch.setattr(socket, "create_connection", boom)
    probe = probe_tcp("no-such-host.invalid", 80, timeout=0.5)
    assert probe.outcome is ProbeOutcome.DNS_ERROR


def test_unreachable_is_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise OSError(101, "Network is unreachable")

    monkeypatch.setattr(socket, "create_connection", boom)
    probe = probe_tcp("203.0.113.10", 80, timeout=0.5)
    assert probe.outcome is ProbeOutcome.UNREACHABLE


@pytest.mark.parametrize("port", [0, -1, 65536, 70000])
def test_port_out_of_range(port: int) -> None:
    with pytest.raises(UsageError) as excinfo:
        validate_port(port)
    assert "1-65535" in excinfo.value.message


@pytest.mark.parametrize("port", ["80", 80.0, True])
def test_port_must_be_integer(port: object) -> None:
    with pytest.raises(UsageError):
        validate_port(port)  # type: ignore[arg-type]


@pytest.mark.parametrize("timeout", [0, -1, 61])
def test_timeout_out_of_range(timeout: float) -> None:
    with pytest.raises(UsageError):
        probe_tcp("127.0.0.1", 80, timeout=timeout)


@pytest.mark.parametrize("host", ["", "   ", "http://user:secret@127.0.0.1"])
def test_invalid_host_is_rejected(host: str) -> None:
    with pytest.raises(UsageError):
        probe_tcp(host, 80)


def test_rejected_host_error_does_not_leak_password() -> None:
    with pytest.raises(UsageError) as excinfo:
        net.validate_host("http://user:s3cret-pw@127.0.0.1")
    assert "s3cret-pw" not in excinfo.value.message


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "LOCALHOST", "[::1]"])
def test_loopback_detection_true(host: str) -> None:
    assert is_loopback(host) is True


@pytest.mark.parametrize("host", ["8.8.8.8", "203.0.113.10", "example.com", "192.168.1.1"])
def test_loopback_detection_false(host: str) -> None:
    assert is_loopback(host) is False


def test_non_loopback_blocked_by_default() -> None:
    with pytest.raises(NetworkError):
        net.ensure_target_allowed("203.0.113.10", allow_non_loopback=False)


def test_non_loopback_allowed_with_flag() -> None:
    net.ensure_target_allowed("203.0.113.10", allow_non_loopback=True)


def test_loopback_allowed_without_flag() -> None:
    net.ensure_target_allowed("127.0.0.1", allow_non_loopback=False)
