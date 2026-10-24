"""SHA-256 计算：正常、跨块、缺失、目录、权限、占用。"""

import hashlib
from pathlib import Path

import pytest

from agent_doctor.core.errors import AccessDeniedError, PathError, UsageError
from agent_doctor.services.hashing import hash_file, normalize_expected_sha256

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_empty_file(tmp_path: Path) -> None:
    target = tmp_path / "empty.bin"
    target.write_bytes(b"")
    digest = hash_file(target)
    assert digest.sha256 == EMPTY_SHA256
    assert digest.size_bytes == 0


def test_known_content(tmp_path: Path) -> None:
    target = tmp_path / "abc.txt"
    target.write_bytes(b"abc")
    assert hash_file(target).sha256 == ABC_SHA256


@pytest.mark.parametrize("chunk_size", [1, 7, 1024, 1024 * 1024])
def test_digest_is_independent_of_chunk_size(tmp_path: Path, chunk_size: int) -> None:
    data = bytes(range(256)) * 9000  # 约 2.3 MB，跨多个 1 MiB 分块
    target = tmp_path / "big.bin"
    target.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert hash_file(target, chunk_size=chunk_size).sha256 == expected


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PathError) as excinfo:
        hash_file(tmp_path / "does-not-exist.bin")
    assert "不存在" in excinfo.value.message


def test_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathError) as excinfo:
        hash_file(tmp_path)
    assert "目录" in excinfo.value.message


def test_permission_error_is_translated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "locked.bin"
    target.write_bytes(b"x")

    def boom(self: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(Path, "open", boom)
    with pytest.raises(AccessDeniedError) as excinfo:
        hash_file(target)
    assert "权限" in excinfo.value.message


def test_sharing_violation_is_reported_as_busy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "busy.bin"
    target.write_bytes(b"x")

    def boom(self: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError(13, "The process cannot access the file", None, 32)

    monkeypatch.setattr(Path, "open", boom)
    with pytest.raises(AccessDeniedError) as excinfo:
        hash_file(target)
    assert "占用" in excinfo.value.message


def test_checked_file_is_not_modified(tmp_path: Path) -> None:
    target = tmp_path / "keep.bin"
    target.write_bytes(b"payload")
    before_bytes = target.read_bytes()
    before_mtime = target.stat().st_mtime_ns

    hash_file(target)

    assert target.read_bytes() == before_bytes
    assert target.stat().st_mtime_ns == before_mtime


def test_invalid_chunk_size(tmp_path: Path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"a")
    with pytest.raises(ValueError, match="chunk_size"):
        hash_file(target, chunk_size=0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD", ABC_SHA256),
        ("sha256:" + ABC_SHA256, ABC_SHA256),
        ("  " + ABC_SHA256 + "  ", ABC_SHA256),
    ],
)
def test_normalize_expected_accepts_common_forms(value: str, expected: str) -> None:
    assert normalize_expected_sha256(value) == expected


@pytest.mark.parametrize("value", ["", "abc", "z" * 64, ABC_SHA256[:-1]])
def test_normalize_expected_rejects_garbage(value: str) -> None:
    with pytest.raises(UsageError):
        normalize_expected_sha256(value)
