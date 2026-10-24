"""PATH 环境变量健康度检查。

只做只读分析：不修改 PATH，也不尝试"修复"任何条目。
"""

import os
from pathlib import Path

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

#: 超过这个长度的 PATH 条目在 Windows 上容易触发长路径问题
MAX_REASONABLE_LENGTH = 240


@check("path.health", "PATH 健康度")
def path_health() -> CheckResult:
    """统计 PATH 中的无效、重复、非 ASCII 和超长条目。"""
    raw = os.environ.get("PATH", "")
    entries = [item.strip().strip('"') for item in raw.split(os.pathsep) if item.strip()]

    if not entries:
        return CheckResult(
            name="path.health",
            status=Status.FAIL,
            summary="PATH 为空",
            details={"entries": 0},
            recommendation="PATH 为空通常意味着环境变量被覆盖，请检查 shell 或系统配置",
        )

    missing = sum(1 for entry in entries if not _is_directory(entry))
    duplicated = len(entries) - len({_normalize(entry) for entry in entries})
    non_ascii = sum(1 for entry in entries if not entry.isascii())
    too_long = sum(1 for entry in entries if len(entry) > MAX_REASONABLE_LENGTH)

    details = {
        "entries": len(entries),
        "missing": missing,
        "duplicated": duplicated,
        "non_ascii": non_ascii,
        "too_long": too_long,
    }

    problems: list[str] = []
    if missing:
        problems.append(f"{missing} 个目录不存在")
    if duplicated:
        problems.append(f"{duplicated} 个重复条目")
    if non_ascii:
        problems.append(f"{non_ascii} 个含非 ASCII 字符")
    if too_long:
        problems.append(f"{too_long} 个超过 {MAX_REASONABLE_LENGTH} 字符")

    if not problems:
        return CheckResult(
            name="path.health",
            status=Status.PASS,
            summary=f"PATH 共 {len(entries)} 项，未发现异常",
            details=details,
        )

    return CheckResult(
        name="path.health",
        status=Status.WARN,
        summary=f"PATH 共 {len(entries)} 项：" + "，".join(problems),
        details=details,
        recommendation="无效条目会拖慢命令解析，建议在系统环境变量里手动清理（本工具不会自动修改）",
    )


def _is_directory(entry: str) -> bool:
    try:
        return Path(entry).is_dir()
    except OSError:
        return False


def _normalize(entry: str) -> str:
    return os.path.normcase(os.path.normpath(entry))
