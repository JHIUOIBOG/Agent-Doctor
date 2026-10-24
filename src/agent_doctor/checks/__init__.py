"""内置检查项。

导入本包即完成注册；注册顺序就是执行顺序，也是 ``check`` 的输出顺序。
"""

from agent_doctor.checks import path_health, platform_info, python_env, toolchain

__all__ = ["path_health", "platform_info", "python_env", "toolchain"]
