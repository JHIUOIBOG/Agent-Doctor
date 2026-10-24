"""路径解析与存在性校验。"""

from pathlib import Path

import pytest

from agent_doctor.core.errors import PathError, UsageError
from agent_doctor.security.paths import normalize_path, require_existing_file


def test_expands_home() -> None:
    assert normalize_path("~") == Path.home()


def test_strips_wrapping_quotes() -> None:
    assert normalize_path('"a.txt"') == Path("a.txt")


def test_relative_path_is_kept_relative() -> None:
    assert normalize_path("sub/dir/a.txt") == Path("sub/dir/a.txt")


@pytest.mark.parametrize("raw", ["", "   ", '""'])
def test_empty_path_is_rejected(raw: str) -> None:
    with pytest.raises(UsageError):
        normalize_path(raw)


def test_null_byte_is_rejected() -> None:
    with pytest.raises(UsageError):
        normalize_path("a\x00b")


def test_existing_file_passes_through(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    target.write_text("x", encoding="utf-8")
    assert require_existing_file(target) == target


def test_missing_file_raises_path_error(tmp_path: Path) -> None:
    with pytest.raises(PathError) as excinfo:
        require_existing_file(tmp_path / "nope.txt")
    assert "不存在" in excinfo.value.message


def test_directory_raises_path_error(tmp_path: Path) -> None:
    with pytest.raises(PathError) as excinfo:
        require_existing_file(tmp_path)
    assert "目录" in excinfo.value.message


def test_stat_permission_error_is_translated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(self: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(Path, "stat", boom)
    with pytest.raises(PathError) as excinfo:
        require_existing_file(tmp_path / "x.txt")
    assert "权限" in excinfo.value.message
