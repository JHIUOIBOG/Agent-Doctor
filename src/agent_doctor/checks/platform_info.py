"""平台与控制台编码检查。"""

import os
import platform
import sys

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

#: 这些编码输出中文容易乱码，是 Windows 上的常见坑
_LEGACY_ENCODINGS = frozenset({"cp936", "gbk", "cp950", "cp932", "cp949", "big5"})


@check("platform.info", "平台信息")
def platform_info() -> CheckResult:
    """识别系统、架构和控制台编码。"""
    encoding = (sys.stdout.encoding or "").lower()
    details = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "console_encoding": encoding or "unknown",
        "is_windows": os.name == "nt",
    }

    if os.name != "nt":
        return CheckResult(
            name="platform.info",
            status=Status.INFO,
            summary=f"{platform.system()} {platform.release()}（非 Windows，部分检查不适用）",
            details=details,
        )

    if encoding in _LEGACY_ENCODINGS:
        return CheckResult(
            name="platform.info",
            status=Status.WARN,
            summary=f"Windows {platform.release()}，控制台编码为 {encoding}",
            details=details,
            recommendation=(
                "中文输出可能乱码；可临时执行 chcp 65001 切换到 UTF-8（本工具不会自动修改）"
            ),
        )

    return CheckResult(
        name="platform.info",
        status=Status.PASS,
        summary=f"Windows {platform.release()}（{platform.machine()}）",
        details=details,
    )
