"""聚合报告模型：多条 :class:`CheckResult` 加一层汇总。"""

from collections import Counter
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

SCHEMA_VERSION = "1.0"


class ToolInfo(BaseModel):
    """生成报告的工具信息。"""

    model_config = ConfigDict(frozen=True)

    name: str = "agent-doctor"
    version: str


class ReportSummary(BaseModel):
    """按状态统计的计数，由 :attr:`DiagnosticReport.summary` 自动计算。"""

    model_config = ConfigDict(frozen=True)

    total: int
    passed: int
    warnings: int
    failures: int
    info: int

    @property
    def has_failures(self) -> bool:
        return self.failures > 0


class DiagnosticReport(BaseModel):
    """一次完整诊断运行的产物。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION)
    tool: ToolInfo
    generated_at: datetime
    results: tuple[CheckResult, ...] = Field(default_factory=tuple)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> ReportSummary:
        counts = Counter(result.status for result in self.results)
        return ReportSummary(
            total=len(self.results),
            passed=counts[Status.PASS],
            warnings=counts[Status.WARN],
            failures=counts[Status.FAIL],
            info=counts[Status.INFO],
        )
