"""``scripts/check_dist.py`` 的单元测试。

构建产物校验必须真的会失败，否则它只是发布前的一次自我安慰。
测试用临时构造的 zip 冒充 wheel，不依赖真实构建。
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest
from scripts import check_dist

if TYPE_CHECKING:
    from pathlib import Path

VALID_ENTRIES = (
    "agent_doctor/__init__.py",
    "agent_doctor/cli/app.py",
    "agent_doctor-0.1.0.dist-info/METADATA",
    "agent_doctor-0.1.0.dist-info/WHEEL",
    "agent_doctor-0.1.0.dist-info/RECORD",
    "agent_doctor-0.1.0.dist-info/entry_points.txt",
    "agent_doctor-0.1.0.dist-info/licenses/LICENSE",
)


def _make_wheel(path: Path, entries: tuple[str, ...]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for entry in entries:
            archive.writestr(entry, "")
    return path


@pytest.fixture
def dist_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    target = tmp_path / "dist"
    target.mkdir()
    monkeypatch.setattr(check_dist, "DIST_DIR", target)
    return target


def test_valid_wheel_passes(dist_dir: Path) -> None:
    wheel = _make_wheel(dist_dir / "agent_doctor-0.1.0-py3-none-any.whl", VALID_ENTRIES)
    assert check_dist.check_wheel(wheel) == []


@pytest.mark.parametrize(
    "extra",
    [
        "tests/unit/test_foo.py",
        "docs/DESIGN.md",
        "scripts/gen_licenses.py",
        ".venv/Lib/site-packages/x.py",
        "agent_doctor/__pycache__/app.cpython-312.pyc",
    ],
)
def test_forbidden_paths_are_reported(dist_dir: Path, extra: str) -> None:
    wheel = _make_wheel(dist_dir / "agent_doctor-0.1.0-py3-none-any.whl", (*VALID_ENTRIES, extra))
    problems = check_dist.check_wheel(wheel)
    assert problems
    assert any(extra in problem for problem in problems)


@pytest.mark.parametrize("missing", check_dist.REQUIRED_SUFFIXES)
def test_missing_required_file_is_reported(dist_dir: Path, missing: str) -> None:
    entries = tuple(e for e in VALID_ENTRIES if not e.endswith(missing))
    wheel = _make_wheel(dist_dir / "agent_doctor-0.1.0-py3-none-any.whl", entries)
    problems = check_dist.check_wheel(wheel)
    assert any(missing in problem for problem in problems)


def test_wheel_without_package_is_reported(dist_dir: Path) -> None:
    # 只留 dist-info，去掉 agent_doctor/ 包本体
    entries = tuple(e for e in VALID_ENTRIES if not e.startswith("agent_doctor/"))
    wheel = _make_wheel(dist_dir / "agent_doctor-0.1.0-py3-none-any.whl", entries)
    assert any("没有 agent_doctor/" in p for p in check_dist.check_wheel(wheel))


def test_no_wheel_exits(dist_dir: Path) -> None:
    with pytest.raises(SystemExit, match="没有 wheel"):
        check_dist.main([])


def test_multiple_wheels_exit(dist_dir: Path) -> None:
    _make_wheel(dist_dir / "a-0.1.0-py3-none-any.whl", VALID_ENTRIES)
    _make_wheel(dist_dir / "b-0.1.0-py3-none-any.whl", VALID_ENTRIES)
    with pytest.raises(SystemExit, match="多个 wheel"):
        check_dist.main([])


def test_main_returns_zero_on_valid_wheel(dist_dir: Path) -> None:
    _make_wheel(dist_dir / "agent_doctor-0.1.0-py3-none-any.whl", VALID_ENTRIES)
    assert check_dist.main([]) == 0


def test_main_returns_one_on_bad_wheel(dist_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _make_wheel(
        dist_dir / "agent_doctor-0.1.0-py3-none-any.whl",
        (*VALID_ENTRIES, "tests/unit/test_foo.py"),
    )
    assert check_dist.main([]) == 1
    assert "校验失败" in capsys.readouterr().err
