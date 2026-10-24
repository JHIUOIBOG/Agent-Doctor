"""路径解析与校验。

所有用户输入的路径都必须经过这里，统一处理 ``~`` 展开、空值、非法字符和类型判断，
避免每个命令各写一遍。
"""

from pathlib import Path

from agent_doctor.core.errors import PathError, UsageError


def normalize_path(raw: str) -> Path:
    """把用户输入的路径字符串变成 :class:`Path`。

    只做解析，不判断存在性——存在性由 :func:`require_existing_file` 负责。
    """
    text = raw.strip().strip('"').strip("'")
    if not text:
        raise UsageError("路径不能为空")
    if "\x00" in text:
        raise UsageError("路径中包含非法字符 NUL")
    try:
        return Path(text).expanduser()
    except (OSError, RuntimeError) as exc:
        raise UsageError(f"无法解析路径：{raw}（{exc}）") from exc


def require_existing_file(path: Path) -> Path:
    """确认路径存在且是普通文件，否则抛出可读的领域异常。"""
    try:
        path.stat()
    except FileNotFoundError as exc:
        raise PathError(f"文件不存在：{path}") from exc
    except PermissionError as exc:
        raise PathError(f"没有访问权限：{path}") from exc
    except OSError as exc:
        raise PathError(f"无法访问路径：{path}（{exc.strerror or exc}）") from exc

    if path.is_dir():
        raise PathError(f"这是一个目录，不是文件：{path}")
    return path
