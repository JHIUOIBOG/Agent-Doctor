#!/usr/bin/env python3
"""生成并校验 `docs/THIRD_PARTY_LICENSES.md`。

依赖清单必须可复现，所以本脚本是唯一的生成入口。CI 用 `--check`
确认提交的清单与当前依赖树一致，避免"装了新依赖却忘了更新清单"。

用法：
    python scripts/gen_licenses.py            # 重新生成清单
    python scripts/gen_licenses.py --check    # 校验（CI 使用），不写文件

`--check` 会同时做两件事，任一失败则退出码为 1：
    1. 许可证策略检查：依赖许可证必须落在白名单内；
    2. 清单一致性检查：磁盘上的清单与重新生成的结果逐字节相同。

清单内容刻意不包含时间戳和 Python 精确版本，否则每次生成都会不同，
`--check` 将永远失败。

**平台约束**：依赖集是平台相关的。``typer`` 依赖
``colorama; platform_system == "Windows"``，Linux 上不会安装。Windows 的依赖
集是两个平台的超集，因此清单**必须在 Windows 上生成**，CI 的 license job 也
跑在 ``windows-latest`` 上。在 Linux 上校验会因缺少 colorama 而不一致。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "docs" / "THIRD_PARTY_LICENSES.md"

# 本项目自身不属于第三方依赖。
IGNORED_PACKAGES = ("agent-doctor",)

# 白名单：只允许宽松许可证。任何不在其中的许可证都会让 CI 失败，
# 迫使新增依赖时人工审查其兼容性。新增条目需要在这里显式放行。
ALLOWED_LICENSES = (
    "MIT",
    "BSD",
    "Apache",
    "ISC",
    "PSF",
    "Python Software Foundation",
    "Unlicense",
    "0BSD",
    "Zlib",
)
ALLOWED_LICENSES_ARG = ";".join(ALLOWED_LICENSES)

HEADER = """# 第三方依赖许可证清单

> **本文件由脚本生成，请勿手工编辑。**
>
> 重新生成：`python scripts/gen_licenses.py`
> 校验（CI 执行）：`python scripts/gen_licenses.py --check`

本项目以 **MIT** 许可证发布。所有运行时与开发依赖必须为宽松许可证
（MIT / BSD / Apache-2.0 / ISC / PSF 等），不得引入 GPL、AGPL、SSPL
等具有传染性或使用限制的许可证。

CI 通过**白名单**强制该政策：默认拒绝未知许可证。新增依赖若使用白名单
之外的许可证，构建会失败，需人工审查后在 `scripts/gen_licenses.py` 的
`ALLOWED_LICENSES` 中显式放行。

> **为什么不用 `--fail-on="GPL;AGPL;SSPL"`**
>
> 该参数默认是精确匹配，而真实许可证字段的写法是 `LGPL-2.1`、
> `GPL-3.0-only`、`GPLv3` 等，精确匹配会全部漏过。本项目实测确认过：
> 对一个声明 `License: LGPL-2.1` 的包，`--fail-on="GPL;AGPL;SSPL"`
> 退出码为 0（放行），加上 `--partial-match` 才为 1。因此改用白名单。

> **为什么不记录版本号**
>
> 依赖用 `>=` 区间声明，CI 每次安装当时的最新版。若清单记录精确版本，
> 任何一次依赖升级都会让清单"过期"，而那与许可证无关，只会制造噪音。
> 清单记录的是**依赖集合与各自的许可证**：包的增删或许可证变更会让
> `--check` 失败，版本漂移不会。

## 清单
"""


def _run_piplicenses(*args: str) -> subprocess.CompletedProcess[str]:
    """调用 pip-licenses 并返回结果。

    命令与参数全部来自本模块的常量，不含外部输入。
    """
    cmd = [
        sys.executable,
        "-m",
        "piplicenses",
        *args,
        "--ignore-packages",
        *IGNORED_PACKAGES,
    ]
    return subprocess.run(  # noqa: S603 - 参数为硬编码常量，不接受外部输入
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def _display_path(path: Path) -> str:
    """尽量用相对路径输出，失败时回退到绝对路径（不因显示问题中断）。"""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _render_table(packages: list[dict[str, object]]) -> str:
    """渲染成 markdown 表格，**不含版本号**。

    版本号会随 CI 安装的最新版漂移，而清单要稳定到只对"依赖集合或许可证
    变化"敏感，所以刻意不记录。
    """
    rows = sorted(packages, key=lambda item: str(item.get("Name", "")).lower())
    lines = ["| Name | License | URL |", "|------|---------|-----|"]
    for item in rows:
        name = str(item.get("Name", "")).strip()
        license_name = str(item.get("License", "")).strip()
        url = str(item.get("URL", "")).strip()
        if url == "UNKNOWN":
            url = ""
        lines.append(f"| {name} | {license_name} | {url} |")
    return "\n".join(lines)


def build_content() -> str:
    """返回完整的清单文件内容（UTF-8 文本，LF 换行）。"""
    proc = _run_piplicenses("--format=json", "--with-urls")
    if proc.returncode != 0:
        raise SystemExit(f"pip-licenses 执行失败：\n{proc.stderr.strip()}")
    raw = proc.stdout.strip()
    if not raw:
        raise SystemExit("pip-licenses 没有返回任何依赖，请确认依赖已安装。")
    try:
        packages = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"无法解析 pip-licenses 的 JSON 输出：{exc}") from exc
    if not packages:
        raise SystemExit("pip-licenses 没有返回任何依赖，请确认依赖已安装。")
    return f"{HEADER}\n{_render_table(packages)}\n"


def check_policy() -> bool:
    """返回依赖许可证是否全部落在白名单内。"""
    proc = _run_piplicenses(f"--allow-only={ALLOWED_LICENSES_ARG}", "--partial-match")
    if proc.returncode == 0:
        return True
    offenders = proc.stdout.strip() or proc.stderr.strip()
    print("许可证策略检查失败，以下依赖的许可证不在白名单内：", file=sys.stderr)
    print(offenders, file=sys.stderr)
    print(
        f"\n白名单：{', '.join(ALLOWED_LICENSES)}\n"
        "如确认该许可证与 MIT 兼容，请在 scripts/gen_licenses.py 的 "
        "ALLOWED_LICENSES 中显式放行。",
        file=sys.stderr,
    )
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="只校验，不写文件；策略违规或清单过期时退出码为 1",
    )
    args = parser.parse_args(argv)

    if not check_policy():
        return 1

    content = build_content()
    encoded = content.encode("utf-8")

    if args.check:
        if not OUTPUT_PATH.exists():
            print(f"清单不存在：{OUTPUT_PATH}", file=sys.stderr)
            return 1
        if OUTPUT_PATH.read_bytes() != encoded:
            print(
                f"清单已过期：{OUTPUT_PATH}\n"
                "请运行 python scripts/gen_licenses.py 重新生成并提交。",
                file=sys.stderr,
            )
            if sys.platform != "win32":
                print(
                    f"注意：当前平台是 {sys.platform}，而清单是在 Windows 上生成的。"
                    "依赖集与平台相关（typer 依赖 "
                    '`colorama; platform_system == "Windows"`），'
                    "在非 Windows 平台校验必然不一致，这不代表清单过期。",
                    file=sys.stderr,
                )
            return 1
        print(f"许可证检查通过：{_display_path(OUTPUT_PATH)}")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(encoded)
    print(f"已写入 {_display_path(OUTPUT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
