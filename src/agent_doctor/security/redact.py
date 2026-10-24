"""脱敏规则。

两条独立的处理链：

1. :func:`redact_paths` —— 把本机绝对路径替换成占位符，避免报告泄露目录结构。
2. :func:`redact_secrets` —— 把形如密钥的字符串替换成 ``<REDACTED:...>``。

两者组合成 :func:`redact`，并且对同一段文本重复调用结果不变（幂等）。
"""

import contextlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any

HOME_PLACEHOLDER = "<HOME>"
TEMP_PLACEHOLDER = "<TEMP>"
CWD_PLACEHOLDER = "<CWD>"

#: ``(正则, 替换)``。顺序有意义：先具体模式，最后兜底的 ``KEY=value``。
_SECRET_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "<REDACTED:OPENAI_KEY>"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}"), "<REDACTED:GH_TOKEN>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}"), "<REDACTED:GH_PAT>"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{12,}"), "<REDACTED:AWS_KEY>"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{8,}"), r"\1 <REDACTED>"),
    # scheme://user:password@host
    (
        re.compile(r"(?P<scheme>[a-zA-Z][\w+.\-]*://)(?P<userinfo>[^/\s@]+)@"),
        r"\g<scheme><REDACTED>@",
    ),
    # 兜底：KEY=value / TOKEN: value。值已经是占位符时跳过，保证幂等。
    (
        re.compile(
            r"(?i)\b([A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS)[A-Z0-9_]*)"
            r"\s*[=:]\s*(?!<REDACTED)[^\s,;\"'}]+"
        ),
        r"\1=<REDACTED>",
    ),
)


def _path_pattern(path: Path) -> re.Pattern[str] | None:
    """为一台机器上的某个目录构造匹配两种分隔符、大小写不敏感的正则。"""
    raw = str(path).rstrip("\\/")
    if not raw:
        return None
    variants = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}
    alternation = "|".join(
        re.escape(variant) for variant in sorted(variants, key=len, reverse=True)
    )
    # 结尾必须是边界，避免 C:\Users\bob 把 C:\Users\bobby 也吃掉
    flags = re.IGNORECASE if os.name == "nt" else 0
    return re.compile(f"(?:{alternation})(?![A-Za-z0-9_.\\-])", flags)


def _default_roots() -> tuple[tuple[Path, str], ...]:
    roots: list[tuple[Path, str]] = []
    with contextlib.suppress(OSError, RuntimeError):
        roots.append((Path(tempfile.gettempdir()), TEMP_PLACEHOLDER))
    with contextlib.suppress(OSError, RuntimeError):
        roots.append((Path.cwd(), CWD_PLACEHOLDER))
    with contextlib.suppress(OSError, RuntimeError):
        roots.append((Path.home(), HOME_PLACEHOLDER))
    return tuple(roots)


def redact_paths(
    text: str,
    *,
    roots: tuple[tuple[Path, str], ...] | None = None,
) -> str:
    """把文本里的本机目录替换成占位符。

    先替换最长的路径（临时目录、工作目录通常比主目录更具体），
    这样 ``<CWD>`` 不会被 ``<HOME>`` 抢先覆盖掉。
    """
    if not text:
        return text
    candidates = roots if roots is not None else _default_roots()
    ordered = sorted(candidates, key=lambda item: len(str(item[0])), reverse=True)
    result = text
    for path, placeholder in ordered:
        pattern = _path_pattern(path)
        if pattern is not None:
            result = pattern.sub(placeholder, result)
    return result


def redact_secrets(text: str) -> str:
    """把疑似凭据替换成占位符。"""
    if not text:
        return text
    result = text
    for pattern, replacement in _SECRET_RULES:
        result = pattern.sub(replacement, result)
    return result


def redact(text: str, *, roots: tuple[tuple[Path, str], ...] | None = None) -> str:
    """路径脱敏 + 凭据脱敏。"""
    return redact_secrets(redact_paths(text, roots=roots))


def redact_value(value: Any, *, roots: tuple[tuple[Path, str], ...] | None = None) -> Any:
    """递归脱敏任意可 JSON 化的结构（dict / list / str）。"""
    if isinstance(value, str):
        return redact(value, roots=roots)
    if isinstance(value, dict):
        return {key: redact_value(item, roots=roots) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(item, roots=roots) for item in value]
    return value
