"""纯文本导出。

不依赖 Rich、不带 ANSI 转义，适合贴进 issue、工单或聊天窗口。
"""

from agent_doctor.models.report import DiagnosticReport
from agent_doctor.security.redact import redact


def render_text(report: DiagnosticReport) -> str:
    """把报告渲染成固定列宽的纯文本，并完成脱敏。"""
    lines: list[str] = [
        f"agent-doctor {report.tool.version} 诊断报告",
        f"生成时间（UTC）：{report.generated_at.isoformat()}",
        f"报告结构版本：{report.schema_version}",
        "",
    ]

    for result in report.results:
        lines.append(f"[{result.status.value.upper():4}] {result.name}: {result.summary}")
        if result.recommendation:
            lines.append(f"       建议: {result.recommendation}")

    summary = report.summary
    lines.extend(
        [
            "",
            f"共 {summary.total} 项：{summary.passed} 通过，{summary.warnings} 警告，"
            f"{summary.failures} 失败，{summary.info} 提示",
        ]
    )
    return redact("\n".join(lines)) + "\n"
