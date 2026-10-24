"""异常层次与退出码契约。

CLI 层只认 :class:`AgentDoctorError`：捕获它、打印 ``message``、以 ``exit_code`` 退出。
其他异常一律视为内部错误（退出码 3），不会把 traceback 喷到 stdout。
"""


class AgentDoctorError(Exception):
    """所有可预期错误的基类。"""

    exit_code: int = 3

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class UsageError(AgentDoctorError):
    """参数或输入不合法（端口越界、哈希格式错误、路径为空等）。"""

    exit_code = 2


class PathError(AgentDoctorError):
    """路径不存在、类型不对或无法访问。"""

    exit_code = 2


class AccessDeniedError(PathError):
    """权限不足或文件被其他进程占用。"""

    exit_code = 2


class NetworkError(AgentDoctorError):
    """网络探测相关的输入错误（非法主机名、被策略拒绝）。"""

    exit_code = 2
