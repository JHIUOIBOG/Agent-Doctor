"""``agent-doctor proxy`` 的端到端行为。"""

import json
import socket

import pytest


def test_connected_to_local_listener(run_cli, listener) -> None:
    outcome = run_cli("proxy", "--host", "127.0.0.1", "--port", str(listener.port))
    assert outcome.exit_code == 0
    assert "连接成功" in outcome.text


def test_connected_json_output(run_cli, listener) -> None:
    outcome = run_cli("proxy", "--host", "127.0.0.1", "--port", str(listener.port), "--json")
    assert outcome.exit_code == 0

    payload = json.loads(outcome.stdout)
    assert payload["name"] == "proxy.tcp"
    assert payload["status"] == "pass"
    assert payload["details"]["outcome"] == "connected"
    assert payload["details"]["port"] == listener.port


def test_closed_port_returns_one(run_cli, free_port) -> None:
    outcome = run_cli("proxy", "--host", "127.0.0.1", "--port", str(free_port), "--json")
    assert outcome.exit_code == 1

    payload = json.loads(outcome.stdout)
    assert payload["status"] == "fail"
    # 防火墙丢包时是 timeout，回 RST 时是 refused，两者都必须判为失败
    assert payload["details"]["outcome"] in {"refused", "timeout"}
    assert payload["recommendation"]


def test_timeout_returns_one(run_cli, monkeypatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", boom)
    outcome = run_cli("proxy", "--host", "127.0.0.1", "--port", "65000", "--timeout", "0.2")
    assert outcome.exit_code == 1
    assert "超时" in outcome.text


@pytest.mark.parametrize("port", ["0", "65536", "70000", "-1"])
def test_invalid_port_returns_two(run_cli, port: str) -> None:
    outcome = run_cli("proxy", "--host", "127.0.0.1", "--port", port)
    assert outcome.exit_code == 2
    assert "1-65535" in outcome.text
    assert "Traceback" not in outcome.text


def test_non_loopback_requires_flag(run_cli) -> None:
    outcome = run_cli("proxy", "--host", "203.0.113.10", "--port", "80")
    assert outcome.exit_code == 2
    assert "allow-non-loopback" in outcome.text


def test_url_host_is_rejected_without_leaking_password(run_cli) -> None:
    outcome = run_cli("proxy", "--host", "http://user:s3cret-pw@127.0.0.1", "--port", "80")
    assert outcome.exit_code == 2
    assert "s3cret-pw" not in outcome.text
    assert "不要传完整 URL" in outcome.text
