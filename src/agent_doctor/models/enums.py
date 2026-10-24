"""诊断结果的领域模型。

只放数据结构与校验规则，不放任何 IO 或渲染逻辑。
"""

from enum import StrEnum


class Status(StrEnum):
    """单条诊断结果的状态。

    取值固定为四个，序列化后即为字符串本身（``Status.PASS == "pass"``）。
    """

    PASS = "pass"  # noqa: S105 - 这是状态值，不是口令
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"

    @property
    def is_problem(self) -> bool:
        """是否属于需要调用方关注（影响退出码）的状态。"""
        return self is Status.FAIL
