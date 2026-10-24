"""``--probe-tool-versions`` 的端到端行为。

核心断言：默认路径**不产生任何子进程**；只有显式开关才会执行外部程序。
"""

import json
import subprocess

from agent_doctor.services import versions

GATED = "toolchain.versions"


class _Counter:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **_kwargs):
        self.calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "git version 2.43.0.windows.1\n", "")


def _patch_run(monkeypatch, counter: _Counter) -> None:
    monkeypatch.setattr(versions.subprocess, "run", counter)


def test_default_check_creates_no_subprocess(run_cli, monkeypatch) -> None:
    counter = _Counter()
    _patch_run(monkeypatch, counter)

    outcome = run_cli("check", "--json")

    assert outcome.exit_code == 0
    assert counter.calls == []
    names = {item["name"] for item in json.loads(outcome.stdout)["results"]}
    assert GATED not in names


def test_probe_flag_adds_version_check(run_cli, monkeypatch) -> None:
    counter = _Counter()
    _patch_run(monkeypatch, counter)

    outcome = run_cli("check", "--probe-tool-versions", "--json")

    assert outcome.exit_code == 0
    payload = json.loads(outcome.stdout)
    names = {item["name"] for item in payload["results"]}
    assert GATED in names
    # 至少对 PATH 里的一个工具发起了 --version
    assert counter.calls
    assert all(cmd[-1] == "--version" for cmd in counter.calls)


def test_probe_flag_reports_versions_in_details(run_cli, monkeypatch) -> None:
    _patch_run(monkeypatch, _Counter())

    outcome = run_cli("check", "--probe-tool-versions", "--json")
    payload = json.loads(outcome.stdout)
    entry = next(item for item in payload["results"] if item["name"] == GATED)

    assert entry["details"]
    assert entry["status"] in {"pass", "warn", "info"}


def test_naming_gated_check_without_flag_exits_two(run_cli) -> None:
    outcome = run_cli("check", "--only", GATED)

    assert outcome.exit_code == 2
    assert "--probe-tool-versions" in outcome.text
    assert "Traceback" not in outcome.text


def test_naming_gated_check_with_flag_succeeds(run_cli, monkeypatch) -> None:
    _patch_run(monkeypatch, _Counter())

    outcome = run_cli("check", "--only", GATED, "--probe-tool-versions", "--json")

    assert outcome.exit_code == 0
    payload = json.loads(outcome.stdout)
    assert [item["name"] for item in payload["results"]] == [GATED]


def test_report_respects_probe_flag(run_cli, monkeypatch) -> None:
    counter = _Counter()
    _patch_run(monkeypatch, counter)

    without = run_cli("report", "--format", "json")
    assert without.exit_code == 0
    assert counter.calls == []
    assert GATED not in {i["name"] for i in json.loads(without.stdout)["results"]}

    with_flag = run_cli("report", "--format", "json", "--probe-tool-versions")
    assert with_flag.exit_code == 0
    assert GATED in {i["name"] for i in json.loads(with_flag.stdout)["results"]}
