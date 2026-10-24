"""Python 解释器检查。"""

import platform
import sys

from agent_doctor.core.registry import check
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult

MINIMUM_VERSION = (3, 12)


@check("python.version", "Python 版本")
def python_version() -> CheckResult:
    """检查当前解释器是否满足最低版本要求。"""
    current = sys.version_info
    version = f"{current.major}.{current.minor}.{current.micro}"
    supported = (current.major, current.minor) >= MINIMUM_VERSION
    return CheckResult(
        name="python.version",
        status=Status.PASS if supported else Status.WARN,
        summary=f"Python {version}",
        details={
            "version": version,
            "implementation": platform.python_implementation(),
            "in_virtualenv": sys.prefix != sys.base_prefix,
        },
        recommendation=None
        if supported
        else f"建议升级到 Python {MINIMUM_VERSION[0]}.{MINIMUM_VERSION[1]} 或更高版本",
    )
