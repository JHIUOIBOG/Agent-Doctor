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
    """一个可执行的检查项。

    :param requires_probe: 标记该检查项会执行外部程序，只有显式开启
        ``--probe-tool-versions`` 时才会被选中。默认路径保持零进程创建。
    """

    name: str
    title: str
    run: CheckFn
    requires_probe: bool = False


_REGISTRY: list[Check] = []


def check(
    name: str,
    title: str,
    *,
    requires_probe: bool = False,
) -> Callable[[CheckFn], CheckFn]:
    """注册装饰器。重复的 ``name`` 会立即失败，避免静默覆盖。"""

    def decorator(func: CheckFn) -> CheckFn:
        if any(existing.name == name for existing in _REGISTRY):
            raise RuntimeError(f"重复注册的检查项：{name}")
        _REGISTRY.append(Check(name=name, title=title, run=func, requires_probe=requires_probe))
        return func

    return decorator


def all_checks() -> tuple[Check, ...]:
    """按注册顺序返回全部检查项（含需要显式开关的）。"""
    return tuple(_REGISTRY)


def select(
    names: Sequence[str] | None = None,
    *,
    probe_versions: bool = False,
) -> tuple[Check, ...]:
    """按名称筛选检查项，保持注册顺序。

    :param names: 要运行的检查项名称；``None`` 表示全部（受 ``probe_versions`` 约束）
    :param probe_versions: 是否包含需要执行外部程序的检查项
    :raises UsageError: 传入了未知的检查项名称，或点名了需要开关却没开启的检查项
    """
    if not names:
        return tuple(item for item in _REGISTRY if probe_versions or not item.requires_probe)

    by_name = {item.name: item for item in _REGISTRY}
    unknown = [name for name in names if name not in by_name]
    if unknown:
        available = ", ".join(sorted(by_name)) or "（无）"
        raise UsageError(f"未知的检查项：{', '.join(unknown)}；可用：{available}")

    gated = [name for name in names if by_name[name].requires_probe]
    if gated and not probe_versions:
        raise UsageError(
            f"检查项 {', '.join(gated)} 会执行外部程序，需要同时传入 --probe-tool-versions 才能运行"
        )

    wanted = set(names)
    return tuple(item for item in _REGISTRY if item.name in wanted)
