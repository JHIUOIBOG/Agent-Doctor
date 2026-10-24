"""单条诊断结果模型。"""

from pydantic import BaseModel, ConfigDict, Field

from agent_doctor.models.enums import Status

#: ``details`` 只允许扁平标量，避免把嵌套对象、文件内容或任意结构塞进报告。
DetailValue = str | bool | int | float | None


class CheckResult(BaseModel):
    """一次诊断的结论。

    该模型是 CLI 输出、JSON 导出和测试断言的共同契约，因此保持冻结且禁止多余字段。
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    name: str = Field(min_length=1, description="检查项标识，例如 ``file.hash``")
    status: Status = Field(description="pass / warn / fail / info")
    summary: str = Field(min_length=1, description="一句话结论，直接展示给用户")
    details: dict[str, DetailValue] = Field(
        default_factory=dict,
        description="扁平的结构化细节，值只能是字符串、布尔、数字或 null",
    )
    recommendation: str | None = Field(
        default=None,
        description="可选的处理建议；只输出文本，永不自动执行",
    )

    @property
    def exit_code(self) -> int:
        """单条结果对应的进程退出码（0 正常，1 发现问题）。"""
        return 1 if self.status.is_problem else 0
