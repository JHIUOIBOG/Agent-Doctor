"""JSON 导出。

脱敏发生在**结构化数据**上而不是序列化之后的字符串上——因为 JSON 会把
``\\`` 转义成 ``\\\\``，在字符串层面替换路径会漏掉。
"""

import json
from typing import Any

from pydantic import BaseModel

from agent_doctor.security.redact import redact_value


def to_serializable(model: BaseModel) -> dict[str, Any]:
    """模型 → 可 JSON 化的 dict，并完成脱敏。"""
    return redact_value(model.model_dump(mode="json"))


def dumps(model: BaseModel, *, indent: int = 2) -> str:
    """序列化为 UTF-8 友好的 JSON 文本（中文不转义，结尾带换行）。"""
    payload = to_serializable(model)
    return json.dumps(payload, ensure_ascii=False, indent=indent) + "\n"
