#!/usr/bin/env python3
"""校验构建产物：``dist/`` 里的 wheel 只应包含运行时代码。

发布前的最后一道闸。防止把测试、文档、虚拟环境或本地临时文件打进 wheel——
这些东西一旦上了 PyPI 就收不回来。

用法：
    python scripts/check_dist.py            # 校验 dist/ 下的 wheel
    python scripts/check_dist.py --build    # 先构建再校验
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"

#: wheel 里允许出现的顶层目录/文件前缀。
ALLOWED_PREFIXES = ("agent_doctor/", "agent_doctor-")

#: 明确不允许出现在 wheel 里的路径片段。
FORBIDDEN_FRAGMENTS = (
    "tests/",
    "docs/",
    "scripts/",
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".github/",
)

#: 必须有这些文件，否则 wheel 装不上或没有入口点。
REQUIRED_SUFFIXES = (
    ".dist-info/METADATA",
    ".dist-info/WHEEL",
    ".dist-info/RECORD",
    ".dist-info/entry_points.txt",
    ".dist-info/licenses/LICENSE",
)


def _find_wheel() -> Path:
    wheels = sorted(DIST_DIR.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"dist/ 下没有 wheel：{DIST_DIR}（先运行 python -m build）")
    if len(wheels) > 1:
        names = ", ".join(path.name for path in wheels)
        raise SystemExit(f"dist/ 下有多个 wheel，无法确定校验对象：{names}")
    return wheels[0]


def check_wheel(wheel: Path) -> list[str]:
    """返回问题列表，空列表表示通过。"""
    problems: list[str] = []

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()

    for name in names:
        if not name.startswith(ALLOWED_PREFIXES):
            problems.append(f"wheel 含非运行时文件：{name}")
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in name:
                problems.append(f"wheel 含不应发布的路径（{fragment}）：{name}")

    for suffix in REQUIRED_SUFFIXES:
        if not any(name.endswith(suffix) for name in names):
            problems.append(f"wheel 缺少必需文件：*{suffix}")

    if not any(name.startswith("agent_doctor/") for name in names):
        problems.append("wheel 里没有 agent_doctor/ 包")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="先运行 python -m build")
    args = parser.parse_args(argv)

    if args.build:
        result = subprocess.run(
            [sys.executable, "-m", "build"],
            cwd=PROJECT_ROOT,
            check=False,
        )
        if result.returncode != 0:
            print("构建失败", file=sys.stderr)
            return 1

    wheel = _find_wheel()
    problems = check_wheel(wheel)

    if problems:
        print(f"构建产物校验失败：{wheel.name}", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(wheel) as archive:
        count = len(archive.namelist())
    print(f"构建产物校验通过：{wheel.name}（{count} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
