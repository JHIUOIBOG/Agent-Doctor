# 发布前审查报告

> 生成时间：2026-10-24 12:05（本地时间，UTC+8）
> 审查对象：`agent-doctor` 仓库 `main` 分支
> 状态：**本地校验全部通过；CI 已运行 4 轮，前 3 轮暴露的问题均已修复，
> 第 4 轮仅剩 license policy 失败，修复结果尚待第 5 轮验证——在亲眼看到
> 6 个 job 全绿之前，不能声称 CI 通过。**

---

## 1. 结论摘要

| 项目 | 结果 |
|------|------|
| 工作区 | 干净，无未提交变更（本次修复前） |
| 待推送提交 | 14 个 |
| 跟踪文件 | 74 个 |
| 本地 Ruff / 格式 | 通过（68 files already formatted） |
| 本地测试 | 284 passed |
| 覆盖率 | 94.94%（门槛 85%） |
| 许可证门禁 | 通过（25 个依赖，全宽松许可） |
| 构建 | wheel + sdist 成功，产物校验通过 |
| wheel 隔离安装 | 四个命令均可运行 |
| 密钥/个人路径扫描 | 未发现真实凭据或个人路径 |
| **CI 实际运行** | **已运行 4 轮；第 4 轮 windows×2 / ubuntu×2 / build 全绿，license policy 失败**（见 §6.1） |

**可以推送验证，但不能据此认为"发布就绪"。** 主要未知项见 §6。

---

## 2. 待推送内容

### 2.1 提交历史（14 个，按时间正序）

```
bd2bfe5  docs: 设计说明 v0.1（阶段 1 交付物）
b6127db  feat: 核心诊断引擎（check / proxy / hash + 159 个测试）
8714129  feat: report 命令 + 文件系统与长路径检查（185 个测试）
2fe81a7  test: 报告契约层（golden 快照 + 字段级约束）
09fa25d  fix: 报告快照被 .gitignore 误伤，只忽略根目录的 report.json
039af55  build: 依赖许可证门禁（白名单 + 清单一致性）
246a7cc  feat: --probe-tool-versions 与发布前构建校验
be59955  docs: 发布前审查报告
dfe4745  chore: 署名统一为 JHIUOIBOG
80ebee4  ci: 修复许可证检查的平台错配，并让 Pytest 失败输出可诊断
ebe328c  fix: 许可证清单不再记录版本号，避免依赖升级导致 CI 误报
0ce093d  docs: 记录 CI 真实结果与推送阻断状态
7b2d6b5  fix: 修复 Ubuntu 上依赖 Windows 语义的测试，并让许可证差异可见
（本次）  fix: 许可证清单改为统计依赖闭包，不再受 CI runner 预装工具影响
```

提交者：`JHIUOIBOG <166821001+JHIUOIBOG@users.noreply.github.com>`（GitHub noreply 邮箱，未泄漏真实邮箱）。

### 2.2 文件构成

```
.github/workflows/ci.yml      3 个 job：test(矩阵) / license / package
docs/                         DESIGN.md、REPORT_SCHEMA.md、THIRD_PARTY_LICENSES.md、RELEASE_CHECK.md
scripts/                      gen_licenses.py、check_dist.py
src/agent_doctor/             1830 行，7 个检查项、4 个命令
tests/                        2566 行，284 个测试
pyproject.toml / README.md / CHANGELOG.md / LICENSE / .gitignore / .gitattributes
```

测试代码量大于源码量（2566 vs 1830），符合"可测试优先"的定位。

---

## 3. 本地校验结果（真实输出）

全部在本机 Windows 11 / Python 3.13.12 的 `.venv` 中执行。

### 3.1 Ruff

```
$ python -m ruff check .
All checks passed!

$ python -m ruff format --check .
68 files already formatted
```

### 3.2 测试与覆盖率

```
$ python -m pytest -q --cov=agent_doctor --cov-report=term-missing --cov-fail-under=85
TOTAL                                         794      34    154      12    95%
Required test coverage of 85% reached. Total coverage: 94.94%
284 passed in 9.16s
```

关键模块覆盖率：`services/versions.py` 100%、`core/registry.py` 100%、
`core/runner.py` 100%、`cli/rendering.py` 100%。

### 3.3 许可证门禁

```
$ python scripts/gen_licenses.py --check
许可证检查通过：docs\THIRD_PARTY_LICENSES.md（25 个依赖）
```

25 个依赖，许可证分布：MIT、BSD-2-Clause、BSD-3-Clause、Apache-2.0、ISC、
PSF-2.0、Apache-2.0 OR BSD-2-Clause。无 GPL / AGPL / SSPL。

本轮把统计口径从"环境里装了什么"改成"项目声明的依赖闭包"（见 §6.1），
因此清单多了三行：`pip-licenses`、`prettytable`、`wcwidth`——它们是
pip-licenses 自身的依赖，此前被 pip-licenses 的 `SYSTEM_PACKAGES` 机制
静默跳过，属于真实存在的漏报。

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
`license` 为独立 job，跑在 `windows-latest` + 3.12（依赖集是平台相关的）；
`package` 跑在 `ubuntu-latest` + 3.12（产物是 `py3-none-any`，与平台无关）。

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

### 6.1 CI 四轮结果：三个问题，两轮修完，最后一轮待验证

| Job | #1 `dfe4745` | #2 `80ebee4` | #3 `ebe328c` | #4 `7b2d6b5` |
|-----|--------------|--------------|--------------|--------------|
| windows-latest / py3.12 | ✅ | ✅ | ✅ | ✅ |
| windows-latest / py3.13 | ✅ | ✅ | ✅ | ✅ |
| ubuntu-latest / py3.12 | ❌ Pytest | ❌ Pytest | ✅ | ✅ |
| ubuntu-latest / py3.13 | ❌ Pytest | ❌ Pytest | ✅ | ✅ |
| build | ✅ | ✅ | ✅ | ✅ |
| license policy | ❌ | ❌ | ❌ | ❌ |

#### 问题一：Ubuntu 上 Pytest 失败（已修复，第 3 轮转绿）

第 1、2 轮 Ubuntu 双版本失败。公开仓库的 job 日志下载需要认证
（`/actions/jobs/{id}/logs` 返回 403），而 `$GITHUB_STEP_SUMMARY` 不进
`check_run.output.summary`，所以当时只能看到"退出码 1"。

第 2 轮先改了 CI：把 Pytest 输出 `tee` 到文件，只把 `FAILED` / `ERROR` 行
转成 `::error::` 注解（覆盖率表格会占满注解配额）。第 3 轮拿到了具体测试名：

```
FAILED tests/unit/test_hashing.py::test_sharing_violation_is_reported_as_busy
assert '占用' in '没有读取权限：/tmp/...'
```

根因：测试用 `PermissionError(13, "...", None, 32)` 的第 4 个参数（`winerror`）
表达 Windows 的文件共享冲突。CPython 在 POSIX 上**不保留**这个参数，属性不存在，
于是代码走"权限不足"分支而不是"文件被占用"分支。

修复：不再依赖构造参数，而是显式设置属性 `exc.winerror = 32`，让两条分支在
两个平台上都能被构造出来。同时补了 `test_permission_error_without_winerror_is_plain_denied`
锁住"没有 winerror 就是普通拒绝"的语义。第 3 轮 Ubuntu 双版本转绿。

#### 问题二：license policy 失败（本轮修复，第 5 轮待验证）

这个 job 连续四轮失败，中间有两次判断不完整，都记在这里：

1. **第一次判断（错）**：以为是平台错配——`typer` 依赖
   `colorama; platform_system == "Windows"`，Linux 不装，清单少一行。于是把
   job 改到 `windows-latest`。第 2 轮仍失败，说明这不是全部原因。
2. **第二次判断（对，但不充分）**：清单记录了精确版本号。依赖用 `>=` 区间
   声明，CI 每次装当时的最新版，字节级比对必然不等。改成不记录版本后，
   第 3 轮 windows 侧不再报版本差异，但 job 依然红。
3. **真实原因**：CI runner 的环境比本地多装了 6 个包。第 4 轮把差异打成注解后
   直接看到了：

   ```
   当前环境有、清单里没有（6 行）：
   + | argcomplete   | Apache Software License | ... |
   + | click         | BSD-3-Clause            | ... |
   + | filelock      | MIT                     | ... |
   + | pipx          | MIT                     | ... |
   + | platformdirs  | MIT                     | ... |
   + | userpath      | MIT                     | ... |
   ```

   这 6 个是 **pipx 及其依赖**，Windows runner 预装。原实现统计的是"整个环境
   装了哪些包"，所以只要 runner 镜像带工具链，清单就会漂移。逐个拉黑不可维护
   ——镜像每次更新都可能多出新的。

**修复（本轮）**：把统计口径从"环境里装了什么"改成"项目声明的依赖闭包"。
从 `pyproject.toml` 的 `dependencies` + `dev` extra 出发，沿已安装分发的
`Requires-Dist` 递归展开，环境标记按**固定的 Windows 目标环境**求值
（而不是按运行脚本的机器），因此同一份清单在任何机器上结果一致。

起点刻意取自 `pyproject.toml` 而不是已安装的 `agent-doctor` 元数据：
`pip install -e .` 会把当时的 Requires-Dist 写进 dist-info，之后改 pyproject
而不重装，元数据就是过期的。**本项目实测踩到了这一点**——新增 `build` /
`pip-licenses` 后，本地元数据里仍然没有它们，按元数据展开会静默漏掉两个依赖。

同时补了三处防护，都有测试锁住：

| 防护 | 测试 |
|------|------|
| 闭包里有、环境里没有的包 → 报错，而不是静默少一行 | `test_build_content_reports_declared_but_missing` |
| 传递依赖的 extra 不得展开（否则 `pytest[testing]` 的可选依赖会混进来） | `test_parse_requirements_ignores_other_extras` |
| 必须带 `--with-system`，否则 pip-licenses 静默跳过它自己和 prettytable/wcwidth | `test_piplicenses_command_uses_closure_and_system_flag` |

顺带发现一个**真实的漏报**：pip-licenses 默认跳过 `SYSTEM_PACKAGES`
（它自己、`prettytable`、`wcwidth`、`pip`、`setuptools`、`wheel`）。前三个
是本项目的 dev 依赖，之前一直没进清单。加 `--with-system` 后它们如实出现，
`pip` / `setuptools` / `wheel` 则因为不在闭包里被自然排除。

**第 5 轮尚未运行**，因此本报告不声称该 job 已通过。

#### 附带发现：本地 venv 曾被破坏

修复过程中发现本地 `.venv` 里 `pip`、`packaging`、`pydantic`、`build`、
`markdown_it`、`mdurl` 的顶层 `.py` 全部丢失（只剩 `__pycache__` 和
`licenses/`），`python -m pip` 报 `No module named pip.__main__`。
这种半坏环境下跑出的测试结果不可信，因此删掉 `.venv` 从零重建后重新安装、
重新跑完全部校验——§3 的数字都来自重建后的环境。


### 6.2 中：Python 3.12 已实测

`windows-latest / py3.12` 与 `ubuntu-latest / py3.12` 均已通过，覆盖了此前
"3.12 未实测"的空白。3.13 同样双平台通过。

### 6.3 中：依赖版本未锁定

`ruff>=0.6`、`pytest>=8.3`、`build>=1.2` 都是下限约束，CI 每次会装当时的最新版。
本地是 `ruff 0.17.2`、`pytest 9.1.1`、`build 1.6.1`。若 CI 装到更新版本并引入新
默认规则，可能出现本地绿、CI 红。没有 lock 文件是当前的实际风险。

对 license job 的影响要单独说明：清单不记录版本号，但**记录许可证字段的文本**。
某个包升级后把 `License: BSD` 写成 `BSD-3-Clause`，清单就会过期。这是刻意的
——许可证写法变化值得看一眼——但它确实会让 CI 变红，不要误判成闭包算错。

### 6.4 低：`--probe-tool-versions` 的行为依赖外部环境

版本探测结果随机器而变，测试用 monkeypatch 隔离了子进程，因此测试稳定；
但真实运行时 `npm` 冷启动可能接近超时上限（已从 3 秒放宽到 10 秒，见 DESIGN.md §15.4）。

### 6.5 低：未实现的既有计划项

- `--no-color` 全局选项未做（依赖 Rich 的 `NO_COLOR` 与非 TTY 降级）；
- mypy 未引入；
- `report` 的 `schema_version` 用手写字段级断言校验，未引入 `jsonschema` 依赖。

---

## 7. 需要人工确认的事项

1. ~~**作者署名（重要）**~~ **已确认**
   署名统一为 `JHIUOIBOG`：`pyproject.toml` 的 `authors` 与 `LICENSE` 的
   `Copyright (c) 2026 JHIUOIBOG` 均已更新。

2. ~~**远端仓库地址与可见性**~~ **已确认**
   `https://github.com/JHIUOIBOG/Agent-Doctor`，**public**，创建时为空仓库（0 KB）。

3. ~~**默认分支名**~~ **已确认**
   GitHub 侧默认分支为 `main`；本地分支仍为 `master`，推送时映射为 `main`。

4. **推送方式**
   空仓库的默认分支由**第一个推送的分支**决定，而修改默认分支需要仓库
   Settings 权限（本机无 `gh`，无法通过 API 改）。因此不推独立分支，直接推
   `main` 建立默认分支，CI 同样会在 push 时触发。若 CI 失败，修复后再推即可。

5. **`AKIA` 误报预案**
   若 GitHub push protection 拦截 `AKIAIOSFODNN7EXAMPLE`，把测试值改成
   `"AKIA" + "IOSFODNN7EXAMPLE"` 之类的拼接形式即可，不影响测试语义。

6. **PyPI 发布**
   本轮不涉及。若后续要发布，`0.1.0` 是不可撤回的版本号，建议先跑通 CI 再考虑。

---

## 8. 建议的下一步

1. 推送本轮修复，看第 5 轮 CI 是否 6 个 job 全绿；
2. 全绿后再更新本报告的 §1 与 §9，把"待验证"改成实测结论；
3. license job 若仍红，第 4 轮加的差异注解会直接给出多出/缺少的行，
   按行判断是"闭包漏算"还是"许可证字段写法变化"；
4. 6 个 job 全绿之前，不发布 PyPI。

---

## 9. 推送状态（本报告更新时）

- 远端：`https://github.com/JHIUOIBOG/Agent-Doctor`，**public**，默认分支 `main`
- 远端 HEAD：`7b2d6b5`
- 本地 HEAD：`7b2d6b5` + 本轮修复（**尚未推送**）

HTTPS 推送被阻断，改用 SSH over 443（`ssh.github.com:443`）后恢复：

| 路径 | 结果 |
|------|------|
| HTTPS 经代理 | `502 CONNECT tunnel failed` |
| HTTPS 直连 | TCP 握手正常（0.15s），TLS `Connection reset` |
| `api.github.com` | 时通时限流（未认证 60 次/小时） |
| `ssh.github.com:443` | **可用**，已成功推送 4 次 |

注意 `git -c http.proxy=` **不能**清空代理，需要 `env -u http_proxy ...`。
推送命令：

```bash
GIT_SSH_COMMAND="ssh -i ~/.ssh/agent_doctor_ed25519 -o StrictHostKeyChecking=accept-new" \
  git push git@ssh.github.com:JHIUOIBOG/Agent-Doctor.git main
```
