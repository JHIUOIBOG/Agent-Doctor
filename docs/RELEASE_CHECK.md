# 发布前审查报告

> 生成时间：2026-10-24 10:45（本地时间，UTC+8）
> 审查对象：`agent-doctor` 仓库当前 `master` 分支
> 状态：**本地校验全部通过；CI 尚未在 GitHub 上运行过，因此不能声称 CI 通过。**

---

## 1. 结论摘要

| 项目 | 结果 |
|------|------|
| 工作区 | 干净，无未提交变更 |
| 待推送提交 | 7 个 |
| 跟踪文件 | 73 个 |
| 本地 Ruff / 格式 | 通过 |
| 本地测试 | 257 passed |
| 覆盖率 | 94.94%（门槛 85%） |
| 许可证门禁 | 通过（22 个依赖，全宽松许可） |
| 构建 | wheel + sdist 成功，产物校验通过 |
| wheel 隔离安装 | 四个命令均可运行 |
| 密钥/个人路径扫描 | 未发现真实凭据或个人路径 |
| **CI 实际运行** | **从未运行，未知** |

**可以推送验证，但不能据此认为"发布就绪"。** 主要未知项见 §6。

---

## 2. 待推送内容

### 2.1 提交历史（7 个，按时间正序）

```
bd2bfe5  docs: 设计说明 v0.1（阶段 1 交付物）
b6127db  feat: 核心诊断引擎（check / proxy / hash + 159 个测试）
8714129  feat: report 命令 + 文件系统与长路径检查（185 个测试）
2fe81a7  test: 报告契约层（golden 快照 + 字段级约束）
09fa25d  fix: 报告快照被 .gitignore 误伤，只忽略根目录的 report.json
039af55  build: 依赖许可证门禁（白名单 + 清单一致性）
246a7cc  feat: --probe-tool-versions 与发布前构建校验
```

提交者：`JHIUOIBOG <166821001+JHIUOIBOG@users.noreply.github.com>`（GitHub noreply 邮箱，未泄漏真实邮箱）。

### 2.2 文件构成

```
.github/workflows/ci.yml      3 个 job：test(矩阵) / license / package
docs/                         DESIGN.md、REPORT_SCHEMA.md、THIRD_PARTY_LICENSES.md
scripts/                      gen_licenses.py、check_dist.py
src/agent_doctor/             1830 行，7 个检查项、4 个命令
tests/                        2230 行，257 个测试
pyproject.toml / README.md / CHANGELOG.md / LICENSE / .gitignore / .gitattributes
```

测试代码量大于源码量（2230 vs 1830），符合"可测试优先"的定位。

---

## 3. 本地校验结果（真实输出）

全部在本机 Windows 11 / Python 3.13.12 的 `.venv` 中执行。

### 3.1 Ruff

```
$ python -m ruff check .
All checks passed!

$ python -m ruff format --check .
67 files already formatted
```

### 3.2 测试与覆盖率

```
$ python -m pytest -q --cov=agent_doctor --cov-report=term-missing --cov-fail-under=85
TOTAL                                         794      34    154      12    95%
Required test coverage of 85% reached. Total coverage: 94.94%
257 passed in 8.79s
```

关键模块覆盖率：`services/versions.py` 100%、`core/registry.py` 100%、
`core/runner.py` 100%、`cli/rendering.py` 100%。

### 3.3 许可证门禁

```
$ python scripts/gen_licenses.py --check
许可证检查通过：docs\THIRD_PARTY_LICENSES.md
```

22 个依赖，许可证分布：MIT、BSD-2-Clause、Apache-2.0、ISC、PSF-2.0、
Apache-2.0 OR BSD-2-Clause。无 GPL / AGPL / SSPL。

### 3.4 构建与产物

```
$ python scripts/check_dist.py --build
Successfully built agent_doctor-0.1.0.tar.gz and agent_doctor-0.1.0-py3-none-any.whl
构建产物校验通过：agent_doctor-0.1.0-py3-none-any.whl（42 个文件）
```

wheel 42 个文件，只含 `agent_doctor/` 与 `.dist-info/`，无 `tests/`、`docs/`、
`scripts/`、`__pycache__`。sdist 63 KB，wheel 41 KB。

### 3.5 wheel 隔离安装验证

在独立 venv 中从 wheel 安装（非 editable），确认导入来源为
`site-packages/agent_doctor`，四个命令均正常：

```
agent-doctor --version                          → agent-doctor 0.1.0
agent-doctor check                              → 6 项：3 通过，3 警告，0 失败
agent-doctor check --probe-tool-versions --only toolchain.versions
                                                → PASS，探测 3 个工具版本
agent-doctor hash README.md                     → PASS SHA-256
agent-doctor report --format text               → 正常渲染
```

### 3.6 Python 最低版本静态检测

```
$ vermin -t=3.12- --no-tips --violations src/ scripts/ tests/
Detecting python files..
Analyzing 62 files using 12 processes..
Minimum required versions: 3.11
Incompatible versions:     2.x
```

代码实际只用到 3.11 特性，对 `requires-python = ">=3.12"` 无违规。
**注意：这是静态检测，不是 3.12 实测。**

---

## 4. CI 配置与本地一致性

| CI 步骤 | CI 命令 | 本地等价命令 | 一致 |
|---------|---------|--------------|------|
| Install | `python -m pip install -e ".[dev]"` | 同 | ✅ |
| Ruff check | `ruff check .` | `python -m ruff check .` | ✅ |
| Ruff format | `ruff format --check .` | 同 | ✅ |
| Pytest | `pytest -q --cov=agent_doctor --cov-report=term-missing --cov-fail-under=85` | 同 | ✅ |
| License | `python scripts/gen_licenses.py --check` | 同 | ✅ |
| Build | `python -m build` | 同 | ✅ |
| Verify wheel | `python scripts/check_dist.py` | 同 | ✅ |

矩阵：`windows-latest` / `ubuntu-latest` × `3.12` / `3.13`，`fail-fast: false`。
`license` 与 `package` 为独立 job，仅 Ubuntu + 3.12 运行。

`pyproject.toml` 的 `pythonpath = ["src", "."]` 是 `tests/unit/test_gen_licenses.py`
能 `from scripts import gen_licenses` 的前提，CI 中同样生效。

---

## 5. 安全检查

| 检查项 | 方法 | 结果 |
|--------|------|------|
| 个人绝对路径 | `git grep` 扫全部 7 个提交 | 无匹配 |
| 邮箱 | 全仓正则 | 无匹配 |
| 凭据模式 | `ghp_` / `github_pat_` / `sk-` / `AKIA` / 私钥头 | 仅命中脱敏规则定义与测试假值 |
| 提交者身份 | `git log --format` | noreply 邮箱 |
| 日志 / 临时文件 | `git ls-files` 扩展名过滤 | 无 |
| 凭据文件 | `.env` / `credential` / `secret` | 无 |
| 最大文件 | 全部跟踪文件 | 29 KB（DESIGN.md） |
| `.gitignore` 覆盖 | 检查 | `.venv/`、`dist/`、`.coverage`、缓存均已忽略 |

唯一需要说明的命中：

- `tests/unit/test_redact.py` 里的 `AKIAIOSFODNN7EXAMPLE` 是 AWS 官方文档的
  示例密钥，不是真实凭据。它可能触发 GitHub push protection 的误报，若被拦截，
  改为字符串拼接即可（见 §7 第 5 条）。

---

## 6. 风险与未验证项

### 6.1 高：CI 从未运行

三个 job、四个矩阵组合全部未在 GitHub 上执行过。以下都是推测而非事实：

- Ubuntu 上 257 个测试是否全绿（测试中无任何 `skipif` 或平台分支，全部假设跨平台）；
- `windows.longpath` 在 Linux 返回 INFO 时，`test_cli_check` 的断言是否仍成立；
- 矩阵四个组合的安装耗时与成功率。

### 6.2 中：Python 3.12 未实测

本机只有 3.13。`vermin` 静态检测最低 3.11，但静态分析不覆盖运行时行为差异
（例如 `datetime.UTC`、`StrEnum` 的确切可用性已在 3.11 落地，风险较低）。

### 6.3 中：依赖版本未锁定

`ruff>=0.6`、`pytest>=8.3`、`build>=1.2` 都是下限约束，CI 每次会装当时的最新版。
本地是 `ruff 0.17.2`、`pytest 9.1.1`、`build 1.6.1`。若 CI 装到更新版本并引入新
默认规则，可能出现本地绿、CI 红。没有 lock 文件是当前的实际风险。

### 6.4 低：`--probe-tool-versions` 的行为依赖外部环境

版本探测结果随机器而变，测试用 monkeypatch 隔离了子进程，因此测试稳定；
但真实运行时 `npm` 冷启动可能接近超时上限（已从 3 秒放宽到 10 秒，见 DESIGN.md §15.4）。

### 6.5 低：未实现的既有计划项

- `--no-color` 全局选项未做（依赖 Rich 的 `NO_COLOR` 与非 TTY 降级）；
- mypy 未引入；
- `report` 的 `schema_version` 用手写字段级断言校验，未引入 `jsonschema` 依赖。

---

## 7. 需要人工确认的事项

1. **作者署名（重要）**
   `pyproject.toml` 当前是 `authors = [{ name = "REDACTED" }]`，
   `LICENSE` 是 `Copyright (c) 2026 REDACTED`。
   这两处会公开出现在仓库、PyPI 元数据和 wheel 里。如果 `REDACTED` 只是脱敏
   占位而不是你想公开的署名，**推送前必须替换**。

2. **远端仓库地址与可见性**
   需要你提供仓库 URL，并明确 public 还是 private。我不会自行创建仓库或改可见性。

3. **默认分支名**
   当前本地是 `master`。GitHub 新建仓库默认 `main`。是否重命名？
   （重命名会改写分支引用，建议在首次推送前决定。）

4. **推送方式**
   建议推到独立分支（如 `ci/verify`）先跑一次 Actions，确认全绿后再合入默认分支。
   需要你确认这个策略，或指定别的分支名。

5. **`AKIA` 误报预案**
   若 GitHub push protection 拦截 `AKIAIOSFODNN7EXAMPLE`，把测试值改成
   `"AKIA" + "IOSFODNN7EXAMPLE"` 之类的拼接形式即可，不影响测试语义。

6. **PyPI 发布**
   本轮不涉及。若后续要发布，`0.1.0` 是不可撤回的版本号，建议先跑通 CI 再考虑。

---

## 8. 建议的下一步

1. 你确认 §7 的第 1–4 条；
2. 我推送到指定远端的目标分支（不碰默认分支、不建 Release）；
3. 观察 Actions 三个 job 的真实结果，把失败项如实记录后再修。

在拿到远端地址之前，不会执行任何推送。
