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

## 清单

| Name              | Version | License                    | URL                                                        |
|-------------------|---------|----------------------------|------------------------------------------------------------|
| Pygments          | 2.21.0  | BSD-2-Clause               | https://pygments.org                                       |
| annotated-doc     | 0.0.5   | MIT                        | https://github.com/fastapi/annotated-doc                   |
| annotated-types   | 0.8.0   | MIT                        | https://github.com/annotated-types/annotated-types         |
| colorama          | 0.4.6   | BSD License                | https://github.com/tartley/colorama                        |
| coverage          | 7.17.0  | Apache-2.0                 | https://github.com/coveragepy/coveragepy                   |
| iniconfig         | 2.3.1   | MIT                        | https://github.com/pytest-dev/iniconfig                    |
| markdown-it-py    | 4.2.0   | MIT License                | https://github.com/executablebooks/markdown-it-py          |
| mdurl             | 0.1.2   | MIT License                | https://github.com/executablebooks/mdurl                   |
| packaging         | 26.3    | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging                          |
| pluggy            | 1.7.0   | MIT License                | https://github.com/pytest-dev/pluggy                       |
| pydantic          | 2.14.1  | MIT                        | https://github.com/pydantic/pydantic                       |
| pydantic_core     | 2.50.1  | MIT                        | https://github.com/pydantic                                |
| pytest            | 9.1.1   | MIT                        | https://docs.pytest.org/en/latest/                         |
| pytest-cov        | 7.1.0   | MIT                        | https://pytest-cov.readthedocs.io/en/latest/changelog.html |
| rich              | 15.0.0  | MIT License                | https://github.com/Textualize/rich                         |
| ruff              | 0.17.2  | MIT                        | https://docs.astral.sh/ruff                                |
| shellingham       | 1.5.4   | ISC License (ISCL)         | https://github.com/sarugaku/shellingham                    |
| typer             | 0.27.3  | MIT                        | https://github.com/fastapi/typer                           |
| typing-inspection | 0.4.4   | MIT                        | https://github.com/pydantic/typing-inspection              |
| typing_extensions | 4.16.0  | PSF-2.0                    | https://github.com/python/typing_extensions                |
