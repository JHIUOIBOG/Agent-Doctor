"""``toolchain.versions`` 检查项的行为。

只测检查项自身的判定逻辑，子进程细节由 ``test_versions.py`` 覆盖。
"""

import pytest

from agent_doctor.checks import toolchain
from agent_doctor.models.enums import Status
from agent_doctor.services.versions import ProbeOutcome, VersionProbe


def _probe(
    command: str,
    outcome: ProbeOutcome,
    version: str | None = None,
    detail: str | None = None,
) -> VersionProbe:
    return VersionProbe(command=command, outcome=outcome, version=version, detail=detail)


@pytest.fixture
def stub_probes(monkeypatch: pytest.MonkeyPatch):
    """替换 probe_all，按传入的探针列表原样返回。"""

    def _install(probes: tuple[VersionProbe, ...]) -> None:
        monkeypatch.setattr(toolchain, "probe_all", lambda _commands: probes)

    return _install


def test_all_ok_is_pass(stub_probes) -> None:
    stub_probes(
        (
            _probe("git", ProbeOutcome.OK, "2.43.0"),
            _probe("node", ProbeOutcome.OK, "20.11.0"),
            _probe("npm", ProbeOutcome.OK, "10.2.4"),
            _probe("uv", ProbeOutcome.OK, "0.1.24"),
        )
    )
    result = toolchain.toolchain_versions()
    assert result.status is Status.PASS
    assert result.details["git"] == "2.43.0"
    assert result.recommendation is None


def test_missing_tools_do_not_warn(stub_probes) -> None:
    """缺失由 toolchain.presence 负责，这里不重复告警。"""
    stub_probes(
        (
            _probe("git", ProbeOutcome.OK, "2.43.0"),
            _probe("node", ProbeOutcome.NOT_FOUND),
            _probe("npm", ProbeOutcome.NOT_FOUND),
            _probe("uv", ProbeOutcome.NOT_FOUND),
        )
    )
    result = toolchain.toolchain_versions()
    assert result.status is Status.PASS
    assert result.details["node"] == "未安装"
    assert "1 个工具版本" in result.summary


def test_nothing_to_probe_is_info(stub_probes) -> None:
    stub_probes(
        (
            _probe("git", ProbeOutcome.NOT_FOUND),
            _probe("node", ProbeOutcome.NOT_FOUND),
            _probe("npm", ProbeOutcome.NOT_FOUND),
            _probe("uv", ProbeOutcome.NOT_FOUND),
        )
    )
    result = toolchain.toolchain_versions()
    assert result.status is Status.INFO
    assert "没有可探测的工具" in result.summary


def test_nonzero_exit_is_warn_and_names_the_tool(stub_probes) -> None:
    stub_probes(
        (
            _probe("git", ProbeOutcome.OK, "2.43.0"),
            _probe("node", ProbeOutcome.FAILED, detail="退出码 1"),
            _probe("npm", ProbeOutcome.NOT_FOUND),
            _probe("uv", ProbeOutcome.NOT_FOUND),
        )
    )
    result = toolchain.toolchain_versions()
    assert result.status is Status.WARN
    assert "Node.js" in result.summary
    assert "npm" not in result.summary
    assert result.details["node"] == "失败（退出码 1）"
    assert result.recommendation


def test_timeout_is_warn(stub_probes) -> None:
    stub_probes((_probe("git", ProbeOutcome.TIMEOUT, detail="超过 3 秒未返回"),))
    result = toolchain.toolchain_versions()
    assert result.status is Status.WARN
    assert "超时" in result.details["git"]


def test_error_is_warn(stub_probes) -> None:
    stub_probes((_probe("git", ProbeOutcome.ERROR, detail="OSError: Access is denied"),))
    result = toolchain.toolchain_versions()
    assert result.status is Status.WARN
    assert "错误" in result.details["git"]


def test_ok_without_version_number_is_still_ok(stub_probes) -> None:
    stub_probes((_probe("git", ProbeOutcome.OK, None, "输出中未找到版本号"),))
    result = toolchain.toolchain_versions()
    assert result.status is Status.PASS
    assert "输出中未找到版本号" in result.details["git"]


def test_check_is_gated_by_probe_flag() -> None:
    """检查项本身必须带 requires_probe 标记，否则默认路径会执行子进程。"""
    from agent_doctor.core.registry import all_checks

    entry = next(item for item in all_checks() if item.name == "toolchain.versions")
    assert entry.requires_probe is True
