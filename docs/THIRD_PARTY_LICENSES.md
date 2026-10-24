# 第三方依赖许可证清单

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

| Name | License | URL |
|------|---------|-----|
| annotated-doc | MIT | https://github.com/fastapi/annotated-doc |
| annotated-types | MIT | https://github.com/annotated-types/annotated-types |
| build | MIT | https://build.pypa.io |
| colorama | BSD License | https://github.com/tartley/colorama |
| coverage | Apache-2.0 | https://github.com/coveragepy/coveragepy |
| iniconfig | MIT | https://github.com/pytest-dev/iniconfig |
| markdown-it-py | MIT License | https://github.com/executablebooks/markdown-it-py |
| mdurl | MIT License | https://github.com/executablebooks/mdurl |
| packaging | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging |
| pluggy | MIT License | https://github.com/pytest-dev/pluggy |
| pydantic | MIT | https://github.com/pydantic/pydantic |
| pydantic_core | MIT | https://github.com/pydantic |
| Pygments | BSD-2-Clause | https://pygments.org |
| pyproject_hooks | MIT | https://github.com/pypa/pyproject-hooks |
| pytest | MIT | https://docs.pytest.org/en/latest/ |
| pytest-cov | MIT | https://pytest-cov.readthedocs.io/en/latest/changelog.html |
| rich | MIT License | https://github.com/Textualize/rich |
| ruff | MIT | https://docs.astral.sh/ruff |
| shellingham | ISC License (ISCL) | https://github.com/sarugaku/shellingham |
| typer | MIT | https://github.com/fastapi/typer |
| typing-inspection | MIT | https://github.com/pydantic/typing-inspection |
| typing_extensions | PSF-2.0 | https://github.com/python/typing_extensions |
