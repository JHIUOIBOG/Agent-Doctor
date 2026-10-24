"""文件 SHA-256 计算。

设计约束：

- **流式读取**，内存占用与文件大小无关（固定 1 MiB 分块）。
- **只读打开**，不修改、不移动、不删除被检查的文件。
- 所有 ``OSError`` 都翻译成带可读信息的领域异常。
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from agent_doctor.core.errors import AccessDeniedError, PathError, UsageError

DEFAULT_CHUNK_SIZE = 1024 * 1024
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
#: Windows 上文件被独占打开时返回的 winerror（ERROR_SHARING_VIOLATION / ERROR_LOCK_VIOLATION）
_SHARING_VIOLATION_CODES = frozenset({32, 33})


@dataclass(frozen=True, slots=True)
class FileDigest:
    """一次哈希计算的结果。"""

    path: Path
    sha256: str
    size_bytes: int


def normalize_expected_sha256(value: str) -> str:
    """校验并归一化用户给出的期望哈希值。

    接受 ``<64位十六进制>``、``sha256:<64位十六进制>`` 和带空格分隔的写法，
    统一转成小写无分隔形式。
    """
    text = value.strip().lower()
    if text.startswith("sha256:"):
        text = text[len("sha256:") :].strip()
    text = text.replace(" ", "")
    if not _SHA256_PATTERN.fullmatch(text):
        raise UsageError("--expected 需要 64 位十六进制 SHA-256 值")
    return text


def hash_file(path: Path, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> FileDigest:
    """计算文件的 SHA-256。

    :raises PathError: 文件不存在、是目录或无法读取
    :raises AccessDeniedError: 没有权限，或文件被其他进程占用
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if path.is_dir():
        raise PathError(f"这是一个目录，不是文件：{path}")

    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
    except FileNotFoundError as exc:
        raise PathError(f"文件不存在：{path}") from exc
    except IsADirectoryError as exc:  # POSIX 下目录会走到这里
        raise PathError(f"这是一个目录，不是文件：{path}") from exc
    except PermissionError as exc:
        raise _translate_permission_error(exc, path) from exc
    except OSError as exc:
        raise PathError(f"读取文件失败：{path}（{exc.strerror or exc}）") from exc

    return FileDigest(path=path, sha256=digest.hexdigest(), size_bytes=size)


def _translate_permission_error(exc: PermissionError, path: Path) -> PathError:
    winerror = getattr(exc, "winerror", None)
    if winerror in _SHARING_VIOLATION_CODES:
        return AccessDeniedError(f"文件被其他进程占用，无法读取：{path}")
    return AccessDeniedError(f"没有读取权限：{path}")
