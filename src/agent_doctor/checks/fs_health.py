"""文件系统健康度：临时目录可写性 + 剩余空间。

这是唯一会写盘的检查项：在系统临时目录里建一个临时文件，关闭即删。
不碰用户目录，不碰任何已有文件。
"""

import shutil
import tempfile
from pathlib import Path

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

#: 低于这个剩余空间就提醒（2 GiB）
MIN_FREE_BYTES = 2 * 1024**3
_GIB = 1024**3


@check("fs.health", "文件系统")
def fs_health() -> CheckResult:
    """检查临时目录能否写入、磁盘是否还有空间。"""
    writable = _temp_dir_writable()

    try:
        usage = shutil.disk_usage(Path.home())
    except OSError as exc:
        return CheckResult(
            name="fs.health",
            status=Status.WARN,
            summary=f"无法读取磁盘空间：{exc.strerror or exc}",
            details={"temp_writable": writable},
            recommendation="检查磁盘或权限设置；本工具不会尝试修复",
        )

    free_gb = round(usage.free / _GIB, 2)
    details = {
        "temp_writable": writable,
        "free_gb": free_gb,
        "total_gb": round(usage.total / _GIB, 2),
    }

    if not writable:
        return CheckResult(
            name="fs.health",
            status=Status.FAIL,
            summary="临时目录不可写",
            details=details,
            recommendation="构建、pip 安装和日志写入都会失败，请检查 TEMP 目录权限",
        )

    if usage.free < MIN_FREE_BYTES:
        return CheckResult(
            name="fs.health",
            status=Status.WARN,
            summary=f"剩余磁盘空间不足：{free_gb} GB",
            details=details,
            recommendation="建议清理磁盘；本工具不会删除任何文件",
        )

    return CheckResult(
        name="fs.health",
        status=Status.PASS,
        summary=f"临时目录可写，剩余 {free_gb} GB",
        details=details,
    )


def _temp_dir_writable() -> bool:
    try:
        with tempfile.NamedTemporaryFile(prefix="agent-doctor-", suffix=".tmp"):
            return True
    except OSError:
        return False
