"""报告落盘。

只做一件事：把文本原子地写到目标路径。先写同目录的临时文件再 ``os.replace``，
这样中途失败不会留下半个 JSON 文件，也不会破坏已存在的旧报告。
"""

import os
import tempfile
from pathlib import Path

from agent_doctor.core.errors import PathError, UsageError


def write_text_atomic(text: str, target: Path, *, force: bool = False) -> Path:
    """把 ``text`` 写入 ``target``。

    :raises UsageError: 目标已存在且没有指定 ``force``
    :raises PathError: 目录不存在、目标是目录或写入失败
    """
    parent = target.parent
    if not parent.is_dir():
        raise PathError(f"输出目录不存在：{parent}")
    if target.exists():
        if target.is_dir():
            raise PathError(f"目标是一个目录：{target}")
        if not force:
            raise UsageError(f"目标文件已存在：{target}；确认覆盖请加 --force")

    fd, temp_name = tempfile.mkstemp(dir=str(parent), prefix=".agent-doctor-", suffix=".tmp")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_path, target)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise PathError(f"写入报告失败：{target}（{exc.strerror or exc}）") from exc
    return target
