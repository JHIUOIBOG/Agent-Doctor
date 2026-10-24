"""受控的子进程版本探测。

默认**不**执行任何外部程序。只有显式传入 ``--probe-tool-versions`` 时本模块才会
被调用，默认路径保持零进程创建。

执行约束（缺一不可）：

- ``shell=False``，参数是固定列表，不接受任何用户输入拼接
- 可执行文件路径来自 :func:`shutil.which`，不是用户给的字符串
- 带超时，避免子进程挂死
- ``stdin`` 指向 ``DEVNULL``，避免子进程等待交互输入
- 只取 stdout 首行并截断长度，避免把大段输出带进报告
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum

LOGGER = logging.getLogger(__name__)

#: 单次探测的超时（秒）。
#:
#: 实测：Windows 上 ``npm --version`` 冷启动约 1.5 秒（Node 首次加载模块 +
#: 杀毒软件扫描），热态同量级。3 秒会偶发误判为超时，故放宽到 10 秒。
#: 误报"探测失败"比多等几秒更糟——那会把用户引向错误的排查方向。
DEFAULT_TIMEOUT = 10.0

#: 版本号字符串的最大长度，超出截断。
MAX_VERSION_LENGTH = 64

#: 从任意输出里抽取版本号，兼容 ``2.43.0.windows.1`` / ``v20.11.0`` / ``uv 0.1.24``。
_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)*(?:[A-Za-z0-9.\-+]*)?")


class ProbeOutcome(StrEnum):
    """一次版本探测的结果类别。"""

    OK = "ok"
    NOT_FOUND = "not_found"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class VersionProbe:
    """一次版本探测的结果。"""

    command: str
    outcome: ProbeOutcome
    version: str | None = None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome is ProbeOutcome.OK


def parse_version(text: str) -> str | None:
    """从 ``--version`` 输出里抽取版本号，找不到返回 ``None``。

    只看第一行：部分工具会在后续行输出构建信息或警告。
    """
    lines = text.strip().splitlines()
    if not lines:
        return None
    match = _VERSION_RE.search(lines[0])
    if match is None:
        return None
    return match.group(0)[:MAX_VERSION_LENGTH]


def probe_version(command: str, *, timeout: float = DEFAULT_TIMEOUT) -> VersionProbe:
    """探测单个命令的版本。任何失败都以 :class:`VersionProbe` 返回，不抛异常。

    :param command: 命令名，例如 ``"git"``；解析结果必须存在于 PATH
    :param timeout: 超时秒数
    """
    executable = shutil.which(command)
    if executable is None:
        LOGGER.debug("命令 %s 不在 PATH 中，跳过版本探测", command)
        return VersionProbe(command=command, outcome=ProbeOutcome.NOT_FOUND)

    try:
        completed = subprocess.run(  # noqa: S603 - 可执行文件来自 which，参数固定
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        LOGGER.debug("命令 %s 版本探测超时（%s 秒）", command, timeout)
        return VersionProbe(
            command=command,
            outcome=ProbeOutcome.TIMEOUT,
            detail=f"超过 {timeout:g} 秒未返回",
        )
    except OSError as exc:
        # 只保留错误类别与系统描述，不把完整路径写进报告。
        LOGGER.debug("命令 %s 版本探测失败：%s", command, exc)
        return VersionProbe(
            command=command,
            outcome=ProbeOutcome.ERROR,
            detail=f"{type(exc).__name__}: {exc.strerror or '无法启动'}",
        )

    if completed.returncode != 0:
        return VersionProbe(
            command=command,
            outcome=ProbeOutcome.FAILED,
            detail=f"退出码 {completed.returncode}",
        )

    version = parse_version(completed.stdout)
    if version is None:
        return VersionProbe(
            command=command,
            outcome=ProbeOutcome.OK,
            detail="输出中未找到版本号",
        )
    return VersionProbe(command=command, outcome=ProbeOutcome.OK, version=version)


def probe_all(
    commands: tuple[str, ...],
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[VersionProbe, ...]:
    """按给定顺序逐个探测，保持顺序稳定（报告需要可复现）。"""
    return tuple(probe_version(command, timeout=timeout) for command in commands)
