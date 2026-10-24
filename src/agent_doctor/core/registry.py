"""检查项注册表。

新增一个检查项只需要在 ``agent_doctor.checks`` 下的模块里用 ``@check(...)`` 装饰一个
返回 :class:`CheckResult` 的函数，不需要改 runner 或 CLI。
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agent_doctor.core.errors import UsageError
from agent_doctor.models.result import CheckResult

CheckFn = Callable[[], CheckResult]


@dataclass(frozen=True, slots=True)
class Check:
    """一个可执行的检查项。"""

    name: str
    title: str
    run: CheckFn


_REGISTRY: list[Check] = []


def check(name: str, title: str) -> Callable[[CheckFn], CheckFn]:
    """注册装饰器。重复的 ``name`` 会立即失败，避免静默覆盖。"""

    def decorator(func: CheckFn) -> CheckFn:
        if any(existing.name == name for existing in _REGISTRY):
            raise RuntimeError(f"重复注册的检查项：{name}")
        _REGISTRY.append(Check(name=name, title=title, run=func))
        return func

    return decorator


def all_checks() -> tuple[Check, ...]:
    """按注册顺序返回全部检查项。"""
    return tuple(_REGISTRY)


def select(names: Sequence[str] | None = None) -> tuple[Check, ...]:
    """按名称筛选检查项，保持注册顺序。

    :raises UsageError: 传入了未知的检查项名称
    """
    if not names:
        return all_checks()
    known = {item.name for item in _REGISTRY}
    unknown = [name for name in names if name not in known]
    if unknown:
        available = ", ".join(sorted(known)) or "（无）"
        raise UsageError(f"未知的检查项：{', '.join(unknown)}；可用：{available}")
    wanted = set(names)
    return tuple(item for item in _REGISTRY if item.name in wanted)
