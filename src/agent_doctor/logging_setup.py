"""日志初始化。

两条纪律：

1. 日志只写 **stderr**，绝不污染 stdout —— 否则 ``report --json`` 的输出会被弄脏。
2. 不记录环境变量值、文件内容或任何凭据；需要定位问题时记录类型名与数量即可。
"""

import logging
import sys

LOGGER_NAME = "agent_doctor"
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(level: str = "WARNING") -> None:
    """配置包级 logger，重复调用是幂等的。"""
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(_resolve_level(level))

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)


def _resolve_level(level: str) -> int:
    candidate = logging.getLevelName(level.strip().upper())
    return candidate if isinstance(candidate, int) else logging.WARNING
