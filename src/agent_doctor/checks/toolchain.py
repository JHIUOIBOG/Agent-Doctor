"""工具链存在性检查。

**只用** ``shutil.which`` 查 PATH，不执行任何外部程序——探测版本需要显式开关，
这是首版刻意保留的最小攻击面。
"""

import shutil

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

#: (命令名, 展示名)
TOOLS: tuple[tuple[str, str], ...] = (
    ("git", "Git"),
    ("node", "Node.js"),
    ("npm", "npm"),
    ("uv", "uv"),
)


@check("toolchain.presence", "工具链")
def toolchain_presence() -> CheckResult:
    """检查常见 AI 编程工具链命令是否在 PATH 中。"""
    found = {command: shutil.which(command) is not None for command, _ in TOOLS}
    missing = [label for command, label in TOOLS if not found[command]]

    if not missing:
        available = "、".join(label for _, label in TOOLS)
        return CheckResult(
            name="toolchain.presence",
            status=Status.PASS,
            summary=f"{available} 均可用",
            details=found,
        )

    return CheckResult(
        name="toolchain.presence",
        status=Status.WARN,
        summary=f"未找到：{'、'.join(missing)}",
        details=found,
        recommendation="如需对应能力请自行安装；本工具不会自动安装，也不会修改系统配置",
    )
