"""`scripts/gen_licenses.py` 的单元测试。

重点是失败路径：许可证策略违规、依赖闭包不完整、清单过期都必须让 CI 失败，
否则门禁形同虚设。真实的 pip-licenses 调用被替换掉，测试不依赖本机装了哪些包；
依赖闭包的计算则用假的分发数据喂进去，不读真实环境。
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from scripts import gen_licenses

if TYPE_CHECKING:
    from pathlib import Path


def _payload(*packages: tuple[str, str, str, str]) -> str:
    """构造 pip-licenses --format=json 的替身输出。"""
    return json.dumps(
        [
            {"Name": name, "Version": version, "License": lic, "URL": url}
            for name, version, lic, url in packages
        ]
    )


FAKE_JSON = _payload(
    ("rich", "15.0.0", "MIT", "https://github.com/Textualize/rich"),
    ("typer", "0.27.3", "MIT", "https://github.com/fastapi/typer"),
)
FAKE_CLOSURE = ("rich", "typer")
OFFENDER_LINE = "license GPL-3.0-only not in allow-only licenses was found for pkg:1.0.0"


def _completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def fake_piplicenses(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """按调用参数返回预设结果，并暴露可修改的状态与调用记录。"""
    state: dict[str, object] = {"policy_ok": True, "payload": FAKE_JSON, "calls": []}
    calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def _fake(*args: str, packages: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
        calls.append((args, tuple(packages)))
        if any(arg.startswith("--allow-only") for arg in args):
            if state["policy_ok"]:
                return _completed(0)
            return _completed(1, stdout=OFFENDER_LINE)
        return _completed(0, stdout=str(state["payload"]))

    state["calls"] = calls
    monkeypatch.setattr(gen_licenses, "_run_piplicenses", _fake)
    # 闭包计算会读真实环境，测试里固定成替身数据。
    monkeypatch.setattr(gen_licenses, "dependency_closure", lambda: FAKE_CLOSURE)
    return state


@pytest.fixture
def output_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """把清单输出重定向到临时目录，避免改动仓库里的真实文件。"""
    target = tmp_path / "docs" / "THIRD_PARTY_LICENSES.md"
    monkeypatch.setattr(gen_licenses, "OUTPUT_PATH", target)
    return target


# --------------------------------------------------------------------------
# 依赖闭包计算
# --------------------------------------------------------------------------


def test_resolve_closure_expands_transitively() -> None:
    closure = gen_licenses._resolve_closure(
        ["typer>=0.27"],
        {
            "typer": ["click>=8"],
            "click": ["colorama; platform_system == 'Windows'"],
            "colorama": [],
        },
    )

    assert closure == ("click", "colorama", "typer")


def test_resolve_closure_uses_target_environment_not_host() -> None:
    """闭包按固定的 Windows 目标环境求值，因此 Linux 上也得到同一结果。"""
    closure = gen_licenses._resolve_closure(
        ["typer"],
        {
            "typer": [
                "colorama; platform_system == 'Windows'",
                "uvloop; sys_platform == 'linux'",
            ],
            "colorama": [],
            "uvloop": [],
        },
    )

    assert closure == ("colorama", "typer")


def test_resolve_closure_excludes_root_package() -> None:
    """清单是"第三方"依赖，项目自身不该出现在里面。"""
    closure = gen_licenses._resolve_closure(
        ["rich"],
        {"agent-doctor": ["rich"], "rich": ["agent-doctor"]},
    )

    assert "agent-doctor" not in closure


def test_resolve_closure_skips_uninstalled_packages() -> None:
    """声明了但没安装的包无法展开，跳过即可——完整性检查会负责报告。"""
    closure = gen_licenses._resolve_closure(["typer", "missing"], {"typer": []})

    assert closure == ("typer",)


def test_resolve_closure_normalizes_names() -> None:
    closure = gen_licenses._resolve_closure(["pydantic_core"], {"pydantic-core": []})

    assert closure == ("pydantic-core",)


def test_resolve_closure_is_sorted() -> None:
    closure = gen_licenses._resolve_closure(["zeta", "alpha"], {"zeta": [], "alpha": []})

    assert closure == ("alpha", "zeta")


def test_resolve_closure_survives_cycles() -> None:
    """依赖图里的环不能让脚本死循环。"""
    closure = gen_licenses._resolve_closure(
        ["a"],
        {"a": ["b"], "b": ["a"]},
    )

    assert closure == ("a", "b")


def test_parse_requirements_includes_dev_extra() -> None:
    names = gen_licenses._parse_requirements(["pytest>=8.3; extra == 'dev'"], extras=("", "dev"))

    assert names == ["pytest"]


def test_parse_requirements_ignores_other_extras() -> None:
    names = gen_licenses._parse_requirements(["sphinx; extra == 'docs'"], extras=("", "dev"))

    assert names == []


def test_parse_requirements_rejects_invalid_spec() -> None:
    with pytest.raises(SystemExit, match="无法解析依赖声明"):
        gen_licenses._parse_requirements(["==="], extras=("",))


def test_declared_requirements_reads_pyproject(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """起点必须是 pyproject.toml：已安装元数据在改过 pyproject 后会过期。"""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
dependencies = ["typer>=0.27"]

[project.optional-dependencies]
dev = ["pytest>=8.3"]
docs = ["mkdocs"]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(gen_licenses, "PYPROJECT", pyproject)

    assert gen_licenses._declared_requirements() == ["typer>=0.27", "pytest>=8.3"]


def test_declared_requirements_fails_without_pyproject(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(gen_licenses, "PYPROJECT", tmp_path / "nope.toml")

    with pytest.raises(SystemExit, match="找不到"):
        gen_licenses._declared_requirements()


def test_installed_requires_normalizes_names(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Dist:
        def __init__(self, name: str | None, requires: list[str]) -> None:
            self.metadata = {"Name": name}
            self.requires = requires

    monkeypatch.setattr(
        gen_licenses.metadata,
        "distributions",
        lambda: [_Dist("PyTest_Cov", ["coverage"]), _Dist(None, ["junk"])],
    )

    assert gen_licenses._installed_requires() == {"pytest-cov": ["coverage"]}


# --------------------------------------------------------------------------
# pip-licenses 调用参数
# --------------------------------------------------------------------------


def test_build_content_requests_closure_only(fake_piplicenses: dict[str, object]) -> None:
    """只按闭包取数，环境里多装的包不该混进清单。"""
    gen_licenses.build_content()

    args, packages = fake_piplicenses["calls"][0]  # type: ignore[index]
    assert packages == FAKE_CLOSURE
    assert "--with-urls" in args


def test_piplicenses_command_uses_closure_and_system_flag() -> None:
    """不加 --with-system 时 pip-licenses 会静默跳过它自己和 prettytable/wcwidth。

    这两个包是本项目的 dev 依赖，被跳过等于清单里凭空少三行。
    """
    cmd = gen_licenses._piplicenses_command("--format=json", packages=("rich", "typer"))

    assert cmd[:3] == [sys.executable, "-m", "piplicenses"]
    assert "--with-system" in cmd
    assert cmd[cmd.index("--packages") + 1 :] == ["rich", "typer"]


def test_piplicenses_command_omits_packages_when_empty() -> None:
    assert "--packages" not in gen_licenses._piplicenses_command("--format=json")


def test_build_content_reports_declared_but_missing(fake_piplicenses: dict[str, object]) -> None:
    """闭包里有、环境里没有的包必须报错，否则清单会静默缺行。"""
    fake_piplicenses["payload"] = _payload(
        ("rich", "15.0.0", "MIT", "https://github.com/Textualize/rich")
    )

    with pytest.raises(SystemExit, match="清单会不完整") as excinfo:
        gen_licenses.build_content()

    assert "typer" in str(excinfo.value)
    assert "pip install -e" in str(excinfo.value)


def test_empty_closure_is_rejected(
    monkeypatch: pytest.MonkeyPatch, fake_piplicenses: dict[str, object]
) -> None:
    monkeypatch.setattr(gen_licenses, "dependency_closure", lambda: ())

    with pytest.raises(SystemExit, match="依赖闭包为空"):
        gen_licenses.build_content()


# --------------------------------------------------------------------------
# 生成与校验
# --------------------------------------------------------------------------


def test_generate_writes_header_and_table(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    assert gen_licenses.main([]) == 0

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# 第三方依赖许可证清单")
    assert "rich" in content
    assert content.endswith("\n")


def test_check_passes_on_fresh_manifest(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen_licenses.main([])
    capsys.readouterr()

    assert gen_licenses.main(["--check"]) == 0
    assert "许可证检查通过" in capsys.readouterr().out


def test_check_fails_when_manifest_is_stale(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen_licenses.main([])
    output_path.write_text("手工改过的旧内容\n", encoding="utf-8")
    capsys.readouterr()

    assert gen_licenses.main(["--check"]) == 1
    assert "清单已过期" in capsys.readouterr().err


def test_check_fails_when_manifest_is_missing(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not output_path.exists()

    assert gen_licenses.main(["--check"]) == 1
    assert "清单不存在" in capsys.readouterr().err


def test_check_fails_on_license_outside_whitelist(
    fake_piplicenses: dict[str, object], output_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen_licenses.main([])
    fake_piplicenses["policy_ok"] = False
    capsys.readouterr()

    assert gen_licenses.main(["--check"]) == 1
    err = capsys.readouterr().err
    assert "许可证策略检查失败" in err
    assert "GPL-3.0-only" in err
    assert "ALLOWED_LICENSES" in err


def test_policy_failure_short_circuits_before_writing(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    """策略违规时不写文件，避免把不合规的清单落盘。"""
    fake_piplicenses["policy_ok"] = False

    assert gen_licenses.main([]) == 1
    assert not output_path.exists()


def test_empty_payload_is_rejected(fake_piplicenses: dict[str, object]) -> None:
    fake_piplicenses["payload"] = "   "

    with pytest.raises(SystemExit, match="没有返回任何依赖"):
        gen_licenses.build_content()


def test_invalid_json_is_rejected(fake_piplicenses: dict[str, object]) -> None:
    fake_piplicenses["payload"] = "not json at all"

    with pytest.raises(SystemExit, match="无法解析"):
        gen_licenses.build_content()


def test_manifest_has_no_version_column(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    gen_licenses.main([])
    content = output_path.read_text(encoding="utf-8")
    assert "| Name | License | URL |" in content
    assert "Version" not in content


def test_version_drift_does_not_expire_manifest(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    """依赖升级只改版本号时，清单不应过期——这是 CI 稳定性的关键。

    依赖用 `>=` 区间声明，CI 每次装最新版；若清单记录精确版本，
    每次依赖升级都会让构建红，而那是噪音。
    """
    gen_licenses.main([])

    fake_piplicenses["payload"] = _payload(
        ("rich", "99.9.9", "MIT", "https://github.com/Textualize/rich"),
        ("typer", "0.99.0", "MIT", "https://github.com/fastapi/typer"),
    )

    assert gen_licenses.main(["--check"]) == 0


def test_added_package_expires_manifest(
    fake_piplicenses: dict[str, object], output_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gen_licenses.main([])

    monkeypatch.setattr(gen_licenses, "dependency_closure", lambda: ("httpx", "rich", "typer"))
    fake_piplicenses["payload"] = _payload(
        ("rich", "15.0.0", "MIT", "https://github.com/Textualize/rich"),
        ("typer", "0.27.3", "MIT", "https://github.com/fastapi/typer"),
        ("httpx", "0.27.0", "BSD-3-Clause", "https://www.python-httpx.org"),
    )

    assert gen_licenses.main(["--check"]) == 1


def test_license_change_expires_manifest(
    fake_piplicenses: dict[str, object], output_path: Path
) -> None:
    """许可证变更必须被发现——这正是清单存在的意义。"""
    gen_licenses.main([])

    fake_piplicenses["payload"] = _payload(
        ("rich", "15.0.0", "Apache-2.0", "https://github.com/Textualize/rich"),
        ("typer", "0.27.3", "MIT", "https://github.com/fastapi/typer"),
    )

    assert gen_licenses.main(["--check"]) == 1


def test_unknown_url_is_blanked(fake_piplicenses: dict[str, object], output_path: Path) -> None:
    fake_piplicenses["payload"] = _payload(
        ("rich", "15.0.0", "MIT", "UNKNOWN"),
        ("typer", "0.27.3", "MIT", "https://github.com/fastapi/typer"),
    )
    gen_licenses.main([])

    content = output_path.read_text(encoding="utf-8")
    assert "| rich | MIT |  |" in content
    assert "UNKNOWN" not in content


def test_diff_reports_added_and_removed_rows(capsys: pytest.CaptureFixture[str]) -> None:
    """--check 失败时必须给出具体差异，否则 CI 只显示"退出码 1"。"""
    on_disk = "# 头部\n| Name | License | URL |\n| old | MIT | u |\n"
    expected = "# 头部\n| Name | License | URL |\n| new | BSD | u |\n"

    gen_licenses._print_diff(on_disk, expected)
    err = capsys.readouterr().err

    assert "+ | new | BSD | u |" in err
    assert "- | old | MIT | u |" in err


def test_diff_ignores_header_changes(capsys: pytest.CaptureFixture[str]) -> None:
    on_disk = "# 旧头部\n| a | MIT | u |\n"
    expected = "# 新头部\n| a | MIT | u |\n"

    gen_licenses._print_diff(on_disk, expected)

    assert capsys.readouterr().err == ""


def test_allowed_licenses_are_lowercase_free_and_semicolon_joined() -> None:
    """白名单参数必须是分号分隔的常量，防止有人塞进逗号导致静默失效。"""
    assert ";" in gen_licenses.ALLOWED_LICENSES_ARG
    assert "," not in gen_licenses.ALLOWED_LICENSES_ARG
    assert gen_licenses.ALLOWED_LICENSES_ARG.split(";") == list(gen_licenses.ALLOWED_LICENSES)
