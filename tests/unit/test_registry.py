"""检查项注册表：内置项、顺序、过滤、重复注册。"""

import pytest

import agent_doctor.checks  # noqa: F401  确保内置检查项已注册
from agent_doctor.core import registry
from agent_doctor.core.errors import UsageError
from agent_doctor.core.registry import all_checks, select
from agent_doctor.models.result import CheckResult

EXPECTED_NAMES = {
    "python.version",
    "platform.info",
    "path.health",
    "toolchain.presence",
    "toolchain.versions",
    "fs.health",
    "windows.longpath",
}

#: 会执行外部程序、必须显式 --probe-tool-versions 才能运行的检查项。
PROBE_GATED = {"toolchain.versions"}


def test_builtin_checks_are_registered() -> None:
    names = {item.name for item in all_checks()}
    assert names == EXPECTED_NAMES


def test_registration_order_is_stable() -> None:
    first = [item.name for item in all_checks()]
    second = [item.name for item in all_checks()]
    assert first == second


def test_every_check_has_title_and_callable() -> None:
    for item in all_checks():
        assert item.title
        assert callable(item.run)


def test_requires_probe_flag_matches_expected() -> None:
    gated = {item.name for item in all_checks() if item.requires_probe}
    assert gated == PROBE_GATED


def test_duplicate_name_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="重复注册"):

        @registry.check("python.version", "重复项")
        def _duplicate() -> CheckResult:  # pragma: no cover - 装饰时就会抛错
            raise AssertionError("不应该被执行")


def test_select_unknown_name_raises() -> None:
    with pytest.raises(UsageError) as excinfo:
        select(["does.not.exist"])
    assert "未知" in excinfo.value.message


def test_select_preserves_registration_order() -> None:
    wanted = ["toolchain.presence", "python.version"]
    selected = [item.name for item in select(wanted)]
    expected = [item.name for item in all_checks() if item.name in wanted]
    assert selected == expected


def test_select_none_returns_default_checks() -> None:
    """默认不含需要开关的检查项，这是"默认零子进程"的落点。"""
    selected = {item.name for item in select(None)}
    assert selected == EXPECTED_NAMES - PROBE_GATED


def test_select_empty_names_returns_default_checks() -> None:
    selected = {item.name for item in select([])}
    assert selected == EXPECTED_NAMES - PROBE_GATED


def test_select_with_probe_returns_everything() -> None:
    assert select(None, probe_versions=True) == all_checks()


def test_naming_gated_check_without_probe_raises() -> None:
    with pytest.raises(UsageError) as excinfo:
        select(["toolchain.versions"])
    assert "probe-tool-versions" in excinfo.value.message


def test_naming_gated_check_with_probe_is_allowed() -> None:
    selected = [item.name for item in select(["toolchain.versions"], probe_versions=True)]
    assert selected == ["toolchain.versions"]
