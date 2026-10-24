"""工具链存在性与版本检查。

存在性检查**只用** ``shutil.which`` 查 PATH，不执行任何外部程序。

版本检查会真正启动子进程，因此标记为 ``requires_probe=True``：只有显式传入
``--probe-tool-versions`` 时才会被选中，默认路径保持零进程创建。
"""

import shutil

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult
from agent_doctor.services.versions import ProbeOutcome, VersionProbe, probe_all

#: (命令名, 展示名)
TOOLS: tuple[tuple[str, str], ...] = (
    ("git", "Git"),
    ("node", "Node.js"),
    ("npm", "npm"),
    ("uv", "uv"),
)

_LABELS = dict(TOOLS)


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


def _describe(probe: VersionProbe) -> str:
    """把探测结果压成适合放进报告的一行文本。"""
    if probe.outcome is ProbeOutcome.OK:
        return probe.version or f"未知（{probe.detail}）"
    if probe.outcome is ProbeOutcome.NOT_FOUND:
        return "未安装"
    if probe.outcome is ProbeOutcome.TIMEOUT:
        return f"超时（{probe.detail}）"
    if probe.outcome is ProbeOutcome.FAILED:
        return f"失败（{probe.detail}）"
    return f"错误（{probe.detail}）"


@check("toolchain.versions", "工具版本", requires_probe=True)
def toolchain_versions() -> CheckResult:
    """探测工具链版本。

    不在 PATH 中的工具记作"未安装"，但**不**让本项变成告警——那属于
    ``toolchain.presence`` 的职责，避免同一个问题报两次。只有"探测到了
    却拿不到版本"才算失败。
    """
    probes = probe_all(tuple(command for command, _ in TOOLS))
    details = {probe.command: _describe(probe) for probe in probes}

    attempted = [p for p in probes if p.outcome is not ProbeOutcome.NOT_FOUND]
    if not attempted:
        return CheckResult(
            name="toolchain.versions",
            status=Status.INFO,
            summary="没有可探测的工具（均不在 PATH 中）",
            details=details,
        )

    broken = [p for p in attempted if not p.ok]
    if not broken:
        return CheckResult(
            name="toolchain.versions",
            status=Status.PASS,
            summary=f"已探测 {len(attempted)} 个工具版本",
            details=details,
        )

    labels = "、".join(_LABELS.get(p.command, p.command) for p in broken)
    return CheckResult(
        name="toolchain.versions",
        status=Status.WARN,
        summary=f"无法获取版本：{labels}",
        details=details,
        recommendation=(
            "手动运行对应命令的 --version 确认是否可执行；本工具不会修复，也不会修改系统配置"
        ),
    )
