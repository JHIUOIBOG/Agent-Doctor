"""共享测试夹具。

原则：不依赖外部网络。端口相关测试只用本机临时监听的 socket，
文件相关测试只用 ``tmp_path``。
"""

import socket
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from typer.testing import CliRunner

import agent_doctor.checks  # noqa: F401  导入即注册内置检查项
from agent_doctor.cli.app import app


@dataclass
class Listener:
    """本机临时监听端口，并记录客户端到底发了什么。"""

    port: int
    received: list[bytes] = field(default_factory=list)
    thread: threading.Thread | None = None

    def wait(self, timeout: float = 2.0) -> None:
        if self.thread is not None:
            self.thread.join(timeout=timeout)


@dataclass
class CliOutcome:
    """一次 CLI 调用的完整结果。"""

    exit_code: int
    stdout: str
    stderr: str

    @property
    def text(self) -> str:
        return self.stdout + self.stderr


def _serve_once(server: socket.socket, sink: list[bytes]) -> None:
    try:
        conn, _ = server.accept()
    except OSError:
        return
    with conn:
        conn.settimeout(0.5)
        try:
            sink.append(conn.recv(4096))
        except (TimeoutError, OSError):
            sink.append(b"")


@pytest.fixture
def listener() -> Iterator[Listener]:
    """真实监听 ``127.0.0.1`` 的一个随机端口。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    sink: list[bytes] = []
    thread = threading.Thread(target=_serve_once, args=(server, sink), daemon=True)
    thread.start()
    result = Listener(port=server.getsockname()[1], received=sink, thread=thread)
    try:
        yield result
    finally:
        server.close()
        thread.join(timeout=2.0)


@pytest.fixture
def free_port() -> int:
    """一个刚被释放、大概率没人监听的本地端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def run_cli() -> Iterator[object]:
    """调用 Typer 应用并返回结构化结果。

    ``catch_exceptions=False``：真出 bug 时让测试直接报错，而不是被悄悄记成 exit_code=1。
    """
    runner = CliRunner()

    def _run(*args: str) -> CliOutcome:
        result = runner.invoke(app, list(args), catch_exceptions=False)
        # typer 0.27 起 CliRunner.Result 分别暴露 stdout / stderr，output 是两者合并
        return CliOutcome(
            exit_code=result.exit_code,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    yield _run
