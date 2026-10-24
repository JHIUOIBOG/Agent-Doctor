"""``agent-doctor hash``：计算文件 SHA-256。"""

import typer

from agent_doctor.cli import rendering
from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult
from agent_doctor.report.json_exporter import dumps
from agent_doctor.security.paths import normalize_path, require_existing_file
from agent_doctor.services.hashing import hash_file, normalize_expected_sha256


def evaluate(raw_path: str, expected: str | None) -> CheckResult:
    """计算哈希并在给出期望值时比对。

    :raises PathError: 路径不存在或不是普通文件
    :raises AccessDeniedError: 没有读权限，或文件被占用
    :raises UsageError: ``--expected`` 格式不合法
    """
    target = require_existing_file(normalize_path(raw_path))
    digest = hash_file(target)

    details: dict[str, str | int | float | bool | None] = {
        "path": str(target),
        "sha256": digest.sha256,
        "size_bytes": digest.size_bytes,
    }

    if expected is None:
        return CheckResult(
            name="file.hash",
            status=Status.PASS,
            summary=f"SHA-256 {digest.sha256}",
            details=details,
        )

    wanted = normalize_expected_sha256(expected)
    details["expected"] = wanted
    if wanted == digest.sha256:
        return CheckResult(
            name="file.hash",
            status=Status.PASS,
            summary="SHA-256 与期望值一致",
            details=details,
        )

    return CheckResult(
        name="file.hash",
        status=Status.FAIL,
        summary="SHA-256 与期望值不一致",
        details=details,
        recommendation="确认文件是否被修改，或核对期望值的来源",
    )


def hash_command(
    path: str = typer.Argument(..., help="要计算 SHA-256 的文件路径"),
    expected: str | None = typer.Option(
        None,
        "--expected",
        "-e",
        help="期望的 SHA-256（64 位十六进制，可带 sha256: 前缀）",
    ),
    json_output: bool = typer.Option(False, "--json", help="以 JSON 输出结果"),
) -> None:
    """计算文件的 SHA-256；给出 --expected 时进行比对。"""
    with rendering.guard():
        result = evaluate(path, expected)
        if json_output:
            typer.echo(dumps(result), nl=False)
        else:
            rendering.render_result(result)
        raise typer.Exit(code=result.exit_code)
