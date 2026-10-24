#!/usr/bin/env python3
"""生成并校验 `docs/THIRD_PARTY_LICENSES.md`。

依赖清单必须可复现，所以本脚本是唯一的生成入口。CI 用 `--check`
确认提交的清单与当前依赖树一致，避免"装了新依赖却忘了更新清单"。

用法：
    python scripts/gen_licenses.py            # 重新生成清单
    python scripts/gen_licenses.py --check    # 校验（CI 使用），不写文件

`--check` 会同时做三件事，任一失败则退出码为 1：
    1. 许可证策略检查：依赖许可证必须落在白名单内；
    2. 闭包完整性检查：声明的依赖必须都已安装（否则清单会静默缺行）；
    3. 清单一致性检查：磁盘上的清单与重新生成的结果逐字节相同。

清单内容刻意不包含时间戳和 Python 精确版本，否则每次生成都会不同，
`--check` 将永远失败。

**为什么统计"依赖闭包"而不是"环境里装了什么"**

最初的做法是让 pip-licenses 列出整个环境。这在本地 venv 里刚好等于依赖集，
但在 GitHub Actions 的 runner 上不成立：Windows runner 预装 pipx 及其依赖
（click / platformdirs / userpath / filelock / argcomplete），这些包会混进
清单，而本地没有，于是 CI 必然失败。逐个拉黑预装包不可维护——runner 镜像
每次更新都可能多出新的。

改为从 `pyproject.toml` 的声明出发，沿已安装分发的 Requires-Dist 递归展开，
只统计项目真正依赖的包。环境里多装了什么与清单无关。

**为什么起点是 pyproject.toml 而不是已安装的元数据**

`pip install -e .` 会把当时的 Requires-Dist 写进 dist-info。之后若修改
pyproject 而没有重装，已安装元数据就是过期的——本项目实测遇到过：
新增 `build` / `pip-licenses` 后元数据里仍然没有，闭包会静默漏掉它们。
pyproject 是声明源头，永远是最新的。

**为什么加 `--with-system`**

pip-licenses 默认会跳过 `SYSTEM_PACKAGES`（pip / setuptools / wheel /
pip-licenses 自身 / prettytable / wcwidth），这是为了不让工具汇报自己。
但 `pip-licenses` 和 `prettytable`、`wcwidth` 确实是 dev 依赖，跳过它们
等于在清单里凭空抹掉三行。加上 `--with-system` 让它们如实出现，
`pip` / `setuptools` / `wheel` 则因为不在依赖闭包里而被自然排除。

**平台约束**

依赖集是平台相关的（`colorama; platform_system == "Windows"`）。闭包按
`TARGET_ENVIRONMENT` 里固定的 Windows 目标环境求值，而不是按运行脚本的机器，
因此生成结果与平台无关，在 Linux 上跑也得到同一份清单。CI 的 license job
仍跑在 `windows-latest` 上，理由见 `docs/RELEASE_CHECK.md`。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "THIRD_PARTY_LICENSES.md"

ROOT_PACKAGE = "agent-doctor"

# CI 只安装 `.[dev]`。其余 extra 的依赖不在这份清单的覆盖范围内，
# 新增 extra 时请在这里登记，否则它的依赖不会被审计。
INSTALLED_EXTRAS = ("dev",)

# 依赖闭包按这个固定的目标环境求值，而不是按运行脚本的机器。
# 全部 10 个标准标记变量都显式给出，避免漏项时回退到真实环境而失去确定性。
TARGET_ENVIRONMENT = {
    "implementation_name": "cpython",
    "implementation_version": "3.12.0",
    "os_name": "nt",
    "platform_machine": "AMD64",
    "platform_python_implementation": "CPython",
    "platform_release": "",
    "platform_system": "Windows",
    "python_full_version": "3.12.0",
    "python_version": "3.12",
    "sys_platform": "win32",
}

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

_NORMALIZE_RE = re.compile(r"[-_.]+")

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

> **清单的范围：依赖闭包，不是当前环境**
>
> 表格里的包是从 `pyproject.toml` 的声明出发、沿 Requires-Dist 递归展开的
> 闭包。环境里额外安装了什么（CI runner 预装的工具、本地临时装的包）不会
> 进入清单，因此同一份清单在任何机器上都能校验通过。

> **为什么不记录版本号**
>
> 依赖用 `>=` 区间声明，CI 每次安装当时的最新版。若清单记录精确版本，
> 任何一次依赖升级都会让清单"过期"，而那与许可证无关，只会制造噪音。
> 清单记录的是**依赖集合与各自的许可证**：包的增删或许可证变更会让
> `--check` 失败，版本漂移不会。

> **为什么不用 `--fail-on="GPL;AGPL;SSPL"`**
>
> 该参数默认是精确匹配，而真实许可证字段的写法是 `LGPL-2.1`、
> `GPL-3.0-only`、`GPLv3` 等，精确匹配会全部漏过。本项目实测确认过：
> 对一个声明 `License: LGPL-2.1` 的包，`--fail-on="GPL;AGPL;SSPL"`
> 退出码为 0（放行），加上 `--partial-match` 才为 1。因此改用白名单。

## 清单
"""


def _normalize(name: str) -> str:
    """按 PEP 503 规范化包名，用于跨来源比对。"""
    return _NORMALIZE_RE.sub("-", name).strip().lower()


def _parse_requirements(raw: Sequence[str], *, extras: tuple[str, ...]) -> list[str]:
    """按目标环境过滤依赖声明，返回应当安装的包名。

    `extras` 是求值环境标记时要尝试的 extra 集合。只有根项目才需要展开
    extra；传递依赖是按不带 extra 的方式安装的，传空字符串即可——若对传递
    依赖也展开 extra，会把 `pytest[testing]` 这类可选依赖误算进来。
    """
    names: list[str] = []
    for text in raw:
        try:
            requirement = Requirement(text)
        except InvalidRequirement as exc:
            raise SystemExit(f"无法解析依赖声明 {text!r}：{exc}") from exc
        if requirement.marker is None:
            names.append(requirement.name)
            continue
        if any(
            requirement.marker.evaluate({**TARGET_ENVIRONMENT, "extra": extra}) for extra in extras
        ):
            names.append(requirement.name)
    return names


def _resolve_closure(
    root_requirements: Sequence[str],
    requires_by_package: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    """展开依赖闭包，返回规范化后的包名（不含项目自身），已排序。

    `requires_by_package` 的键是规范化包名，值是 Requires-Dist 原始字符串。
    声明了但没安装的包会被跳过——它无法继续展开，且 `build_content` 的
    完整性检查会把它报出来。
    """
    closure: set[str] = set()
    visited: set[str] = set()
    stack = _parse_requirements(root_requirements, extras=("", *INSTALLED_EXTRAS))

    while stack:
        key = _normalize(stack.pop())
        if key in visited:
            continue
        visited.add(key)
        requires = requires_by_package.get(key)
        if requires is None:
            continue
        closure.add(key)
        stack.extend(_parse_requirements(requires, extras=("",)))

    closure.discard(_normalize(ROOT_PACKAGE))
    return tuple(sorted(closure))


def _declared_requirements() -> list[str]:
    """从 pyproject.toml 读取根依赖声明（含已登记的 extra）。"""
    if not PYPROJECT.is_file():
        raise SystemExit(f"找不到 {PYPROJECT}，无法确定依赖声明。")
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    declared = list(project.get("dependencies") or [])
    optional = project.get("optional-dependencies") or {}
    for extra, requirements in optional.items():
        if extra in INSTALLED_EXTRAS:
            declared.extend(requirements)
    return declared


def _installed_requires() -> dict[str, list[str]]:
    """收集当前环境里各分发的 Requires-Dist。"""
    mapping: dict[str, list[str]] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue
        mapping.setdefault(_normalize(name), list(dist.requires or []))
    return mapping


def dependency_closure() -> tuple[str, ...]:
    """返回项目依赖闭包（规范化包名，已排序，不含项目自身）。"""
    return _resolve_closure(_declared_requirements(), _installed_requires())


def _piplicenses_command(*args: str, packages: Sequence[str] = ()) -> list[str]:
    """构造 pip-licenses 命令行。

    `--with-system` 不能省：pip-licenses 默认会跳过 `SYSTEM_PACKAGES`
    （它自己、prettytable、wcwidth、pip、setuptools、wheel），而前三个
    确实是本项目的 dev 依赖，跳过等于在清单里凭空抹掉三行。pip /
    setuptools / wheel 则因为不在依赖闭包里而被 `--packages` 自然排除。
    """
    cmd = [sys.executable, "-m", "piplicenses", *args, "--with-system"]
    if packages:
        cmd.extend(["--packages", *packages])
    return cmd


def _run_piplicenses(*args: str, packages: Sequence[str] = ()) -> subprocess.CompletedProcess[str]:
    """调用 pip-licenses 并返回结果。

    命令与参数全部来自本模块的常量与闭包结果，不接受外部输入。
    """
    return subprocess.run(  # noqa: S603 - 参数为常量与闭包结果，不接受外部输入
        _piplicenses_command(*args, packages=packages),
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


def _table_rows(text: str) -> set[str]:
    """只取表格行，忽略说明性头部（头部改动不该淹没依赖差异）。"""
    return {line for line in text.splitlines() if line.startswith("|")}


def _print_diff(on_disk: str, expected: str, *, limit: int = 20) -> None:
    """打印清单与当前依赖的差异，便于在 CI 日志里直接看出原因。"""
    disk_rows = _table_rows(on_disk)
    expected_rows = _table_rows(expected)

    added = sorted(expected_rows - disk_rows)
    removed = sorted(disk_rows - expected_rows)

    if added:
        print(f"当前依赖有、清单里没有（{len(added)} 行）：", file=sys.stderr)
        for line in added[:limit]:
            print(f"  + {line}", file=sys.stderr)
        if len(added) > limit:
            print(f"  …还有 {len(added) - limit} 行", file=sys.stderr)
    if removed:
        print(f"清单里有、当前依赖没有（{len(removed)} 行）：", file=sys.stderr)
        for line in removed[:limit]:
            print(f"  - {line}", file=sys.stderr)
        if len(removed) > limit:
            print(f"  …还有 {len(removed) - limit} 行", file=sys.stderr)


def build_content(packages: Sequence[str] | None = None) -> str:
    """返回完整的清单文件内容（UTF-8 文本，LF 换行）。"""
    names = tuple(packages) if packages is not None else dependency_closure()
    if not names:
        raise SystemExit("依赖闭包为空，请确认 pyproject.toml 里的 dependencies 已声明。")

    proc = _run_piplicenses("--format=json", "--with-urls", packages=names)
    if proc.returncode != 0:
        raise SystemExit(f"pip-licenses 执行失败：\n{proc.stderr.strip()}")
    raw = proc.stdout.strip()
    if not raw:
        raise SystemExit("pip-licenses 没有返回任何依赖，请确认依赖已安装。")
    try:
        found = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"无法解析 pip-licenses 的 JSON 输出：{exc}") from exc
    if not found:
        raise SystemExit("pip-licenses 没有返回任何依赖，请确认依赖已安装。")

    # 声明了却拿不到许可证，说明环境没装齐。若不在这里拦下，清单会静默
    # 少几行，而"少了几行"看起来和"依赖变少了"一模一样，没人会发现。
    reported = {_normalize(str(item.get("Name", ""))) for item in found}
    absent = [name for name in names if _normalize(name) not in reported]
    if absent:
        detail = "\n".join(f"  - {name}" for name in absent)
        hint = ""
        if sys.platform != "win32":
            hint = (
                "\n注意：依赖闭包按 Windows 目标环境求值，`colorama` 这类条件依赖"
                f"在 {sys.platform} 上不会被安装。清单必须在 Windows 上生成与校验。"
            )
        raise SystemExit(
            f"以下依赖已声明但当前环境没有安装，清单会不完整：\n{detail}\n"
            '请先运行 pip install -e ".[dev]" 重新安装依赖。' + hint
        )

    return f"{HEADER}\n{_render_table(found)}\n"


def check_policy(packages: Sequence[str] | None = None) -> bool:
    """返回依赖许可证是否全部落在白名单内。"""
    names = tuple(packages) if packages is not None else dependency_closure()
    proc = _run_piplicenses(
        f"--allow-only={ALLOWED_LICENSES_ARG}", "--partial-match", packages=names
    )
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

    packages = dependency_closure()

    if not check_policy(packages):
        return 1

    content = build_content(packages)
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
            _print_diff(OUTPUT_PATH.read_text(encoding="utf-8"), content)
            return 1
        print(f"许可证检查通过：{_display_path(OUTPUT_PATH)}（{len(packages)} 个依赖）")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(encoded)
    print(f"已写入 {_display_path(OUTPUT_PATH)}（{len(packages)} 个依赖）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
