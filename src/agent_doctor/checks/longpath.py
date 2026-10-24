"""Windows 长路径开关检查。

**只读**注册表：只调用 ``OpenKey`` / ``QueryValueEx``，不写入任何键值。
遇到读不到的情况降级为 warn，而不是报错。
"""

import os

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

_IS_WINDOWS = os.name == "nt"
_REGISTRY_KEY = r"SYSTEM\CurrentControlSet\Control\FileSystem"
_VALUE_NAME = "LongPathsEnabled"


@check("windows.longpath", "长路径支持")
def long_paths() -> CheckResult:
    """检查 Windows 是否启用了长路径支持。"""
    if not _IS_WINDOWS:
        return CheckResult(
            name="windows.longpath",
            status=Status.INFO,
            summary="非 Windows 平台，跳过长路径检查",
            details={"is_windows": False},
        )

    value = _read_long_paths_flag()
    if value is None:
        return CheckResult(
            name="windows.longpath",
            status=Status.WARN,
            summary="无法读取 LongPathsEnabled 注册表值",
            details={"is_windows": True},
            recommendation=(
                "可手动确认 HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem 下的 "
                "LongPathsEnabled；本工具不会修改注册表"
            ),
        )

    enabled = value == 1
    return CheckResult(
        name="windows.longpath",
        status=Status.PASS if enabled else Status.WARN,
        summary=(
            "已启用长路径支持" if enabled else "未启用长路径支持（超过 260 字符的路径可能失败）"
        ),
        details={"is_windows": True, "long_paths_enabled": enabled},
        recommendation=None
        if enabled
        else "如遇长路径报错，可手动启用 LongPathsEnabled（组策略或注册表）；本工具不会自动修改",
    )


def _read_long_paths_flag() -> int | None:
    """读取注册表值；读不到返回 ``None``。"""
    try:
        import winreg  # 仅 Windows 存在，因此延迟导入
    except ImportError:  # pragma: no cover - 非 Windows 才会走到
        return None

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _REGISTRY_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
    except OSError:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
