# Agent Doctor 设计说明 v0.1

- 状态：**待确认**（确认后进入 S1 垂直切片）
- 日期：2026-10-24
- 目标运行时：Python 3.12+ / Windows 10 1809+（同时保证在 macOS、Linux 上可运行、可测试）
- 本文档只描述结构与契约，不含实现代码。

---

## 1. 目标与非目标

### 1.1 目标

| # | 目标 | 判定方式 |
|---|------|----------|
| G1 | 一条命令看清本机 AI 编程环境是否可用 | `agent-doctor check` 输出结论 + 建议 |
| G2 | 输出可被 CI / 工单系统消费的结构化报告 | `agent-doctor report --format json` 通过 JSON Schema 校验 |
| G3 | 本地端口连通性可自查（代理、模型服务） | `agent-doctor proxy` 给出 open/refused/timeout 分类与耗时 |
| G4 | 文件校验可复现 | `agent-doctor hash` 输出与 `certutil -hashfile` / `sha256sum` 一致 |
| G5 | 代码可维护、可测试、可发布 | Ruff 零告警、pytest 全绿、CI 双平台通过 |

### 1.2 非目标（首版明确不做）

- 不做 GUI / TUI 交互界面
- 不做数据库、账号、云同步、遥测
- **不做任何自动修复**，只输出建议文本
- 不上传文件、日志、报告
- 不读取、不打印、不校验 API 密钥值
- 不修改系统环境变量、注册表、其他应用配置

---

## 2. 依赖与许可证核查（已完成）

已通过 PyPI 元数据与本地实测核对，全部为宽松许可，与 MIT 兼容：

| 依赖 | 用途 | 版本 | 许可证 | 与 MIT 兼容 |
|------|------|------|--------|-------------|
| typer | CLI 框架 | 0.27.3 | MIT | 是 |
| rich | 终端渲染 | 15.0.0 | MIT | 是 |
| pydantic | 数据模型/校验 | 2.14.1 | MIT | 是 |
| pytest | 测试 | 9.1.1 | MIT | 是 |
| pytest-cov | 覆盖率 | 7.1.0 | MIT | 是 |
| ruff | 检查/格式化 | 0.17.2 | MIT | 是 |
| pip-licenses | 许可证审计（仅开发） | 5.5.5 | MIT | 是 |

**结论：项目可采用 MIT 许可证。**

> 与初稿的差异：初稿计划用 `pydantic-settings` 加载配置，实现时判断单机诊断
> 工具不需要外部配置源，改用 Pydantic 模型 + 默认值，该依赖已移除；初稿担心
> typer 会引入 `click`，但 0.27 起 typer 已不再依赖 click。

间接依赖由 `docs/THIRD_PARTY_LICENSES.md` 完整登记（当前 20 个包），
初稿悬而未决的 `annotated-doc` 已确认为 **MIT**。

### 2.1 许可证门禁（已落地）

清单由脚本生成，CI 负责校验：

```bash
python scripts/gen_licenses.py          # 重新生成清单
python scripts/gen_licenses.py --check  # CI 执行：策略检查 + 清单一致性
```

> **不使用 `pip-licenses --fail-on="GPL;AGPL;SSPL"`。**
>
> 初稿写的这条命令实际无效：`--fail-on` 默认是精确匹配，而真实许可证字段
> 是 `LGPL-2.1`、`GPL-3.0-only`、`GPLv3` 等写法，会全部漏过。已实测：对声明
> `License: LGPL-2.1` 的包，该命令退出码为 **0（放行）**，加 `--partial-match`
> 才为 1。
>
> 现改用**白名单**（默认拒绝）：`--allow-only="MIT;BSD;Apache;ISC;PSF;..."`
> 配合 `--partial-match`。新增依赖若使用白名单外的许可证，CI 会失败并要求
> 人工审查后显式放行。清单一致性检查可防止"装了新依赖但忘了更新清单"。

---

## 3. 目录结构

```
agent-doctor/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── DESIGN.md                 # 本文档
│   ├── SECURITY.md               # 威胁模型与控制措施
│   ├── REPORT_SCHEMA.md          # 报告字段说明（面向消费者）
│   ├── THIRD_PARTY_LICENSES.md   # 依赖许可证清单（自动生成）
│   └── adr/
│       └── 0001-single-diagnostic-pipeline.md
├── src/
│   └── agent_doctor/
│       ├── __init__.py           # 仅导出 __version__
│       ├── __main__.py           # python -m agent_doctor 入口
│       ├── cli/
│       │   ├── app.py            # Typer 装配、全局选项、异常→退出码
│       │   ├── rendering.py      # Rich 表格/面板、颜色降级
│       │   └── commands/
│       │       ├── check.py
│       │       ├── proxy.py
│       │       ├── hash.py
│       │       └── report.py
│       ├── core/
│       │   ├── context.py        # RunContext：settings/clock/logger/redactor
│       │   ├── errors.py         # 异常层次与退出码映射
│       │   ├── registry.py       # 检查项注册、排序、过滤
│       │   └── runner.py         # 执行检查并组装 DiagnosticReport
│       ├── models/
│       │   ├── enums.py          # Status / Severity
│       │   ├── result.py         # CheckResult / Finding
│       │   ├── report.py         # DiagnosticReport / Summary / Environment
│       │   └── settings.py       # Settings（pydantic-settings）
│       ├── checks/
│       │   ├── base.py           # Check 协议 + 注册装饰器
│       │   ├── python_env.py     # 解释器版本、venv
│       │   ├── platform_info.py  # OS/架构/控制台编码
│       │   ├── path_health.py    # PATH 有效性、重复、非 ASCII、超长
│       │   ├── toolchain.py      # git/node/uv 存在性（不执行）
│       │   ├── fs_health.py      # 可写性探测、磁盘空间
│       │   └── longpath.py       # Windows 长路径开关（只读注册表）
│       ├── services/
│       │   ├── hashing.py        # 流式 SHA-256
│       │   └── net.py            # TCP 端口探测
│       ├── security/
│       │   ├── paths.py          # 安全路径解析与校验
│       │   └── redact.py         # 脱敏规则引擎
│       ├── report/
│       │   ├── base.py           # Exporter 协议
│       │   ├── json_exporter.py
│       │   └── text_exporter.py
│       └── logging/
│           └── setup.py          # 日志初始化与敏感信息过滤器
├── tests/
│   ├── conftest.py               # 共享 fixture：tmp_path 工厂、fake clock、CliRunner
│   ├── unit/
│   │   ├── test_hashing.py
│   │   ├── test_net.py
│   │   ├── test_redact.py
│   │   ├── test_paths.py
│   │   ├── test_settings.py
│   │   ├── test_registry.py
│   │   ├── test_runner.py
│   │   └── test_exporters.py
│   ├── integration/
│   │   ├── test_cli_check.py
│   │   ├── test_cli_proxy.py
│   │   ├── test_cli_hash.py
│   │   ├── test_cli_report.py
│   │   └── test_exit_codes.py
│   └── contract/
│       └── test_report_schema.py # golden JSON + jsonschema 校验
├── .gitignore
├── .editorconfig
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                       # MIT
├── README.md
└── pyproject.toml
```

设计约束：`cli/` 不 import `services/`；`checks/` 不 import `cli/`；`report/` 只依赖 `models/` 与 `security/`。依赖方向单向向下，由 `tests/unit/test_architecture.py` 用 AST 扫描断言。

---

## 4. 模块职责与验收标准

### 4.1 CLI 层

| 模块 | 职责 | 验收标准（可测） |
|------|------|------------------|
| `cli/app.py` | 装配 Typer、注册 4 个子命令、全局选项（`--log-level`、`--no-color`、`--version`）、统一把 `AgentDoctorError` 映射为退出码 | `agent-doctor --help` 列出 4 个命令；未知参数退出码 2；`--version` 不触发任何检查、不联网 |
| `cli/commands/check.py` | 调用 `runner.run_diagnostics()`，用 `rendering` 渲染 | 命令函数 ≤ 25 行；无业务逻辑；可被 `CliRunner` 独立测试 |
| `cli/commands/proxy.py` | 校验 host/port 参数后调用 `services.net` | 非法端口（0、65536、字符串）退出码 2 且提示明确 |
| `cli/commands/hash.py` | 校验路径后调用 `services.hashing` | 不存在/是目录/无权限分别返回退出码 2 且信息可读 |
| `cli/commands/report.py` | 复用同一条诊断管道，交给 exporter 序列化 | `--format json` 输出可被 `json.loads` 解析；不混入 Rich 装饰字符 |
| `cli/rendering.py` | Rich 表格/面板、状态图标、`NO_COLOR` 与非 TTY 降级 | 管道输出（非 TTY）不含 ANSI 转义；`--no-color` 生效 |

### 4.2 领域层（models / core）

| 模块 | 职责 | 验收标准（可测） |
|------|------|------------------|
| `models/enums.py` | `Status = ok/warn/error/skipped`、`Severity = info/warn/error` | 枚举值与 JSON 输出一致，有快照测试 |
| `models/result.py` | `CheckResult`（id、title、status、severity、message、details、duration_ms）、`Finding`（建议文本） | frozen 模型；`details` 只允许标量/字符串；序列化稳定 |
| `models/report.py` | `DiagnosticReport`（schema_version、tool、generated_at、environment、summary、checks），summary 自动由 checks 计算 | 与 golden JSON 完全一致；summary 计数不可手工赋值 |
| `models/settings.py` | pydantic-settings，前缀 `AGENT_DOCTOR_`，优先级 CLI > env > 默认 | 非法值给出中文错误并退出码 2；未知 env 变量不导致崩溃 |
| `core/errors.py` | 异常层次：`AgentDoctorError` → `UsageError` / `PathError` / `PermissionError` / `NetworkError` / `InternalError`，每类带 `exit_code` | 每个异常类有单测；未捕获异常只记日志，不写入报告，不打印堆栈到 stdout |
| `core/registry.py` | 检查项注册（装饰器）、稳定排序、`--only/--skip` 过滤 | 顺序确定（按注册顺序）；重复 id 注册抛错；未知 id 过滤时给出警告 |
| `core/context.py` | `RunContext`：settings、`clock: Callable[[], datetime]`、logger、redactor | 注入 fake clock 后报告时间可预测（golden 测试依赖此项） |
| `core/runner.py` | 逐个执行检查，捕获异常转 `status=error`，组装报告 | 某检查抛 `RuntimeError` 时整体仍返回报告且 `summary.error == 1`；单检查超时不阻塞整体 |

### 4.3 采集层（checks / services）

| 模块 | 职责 | 验收标准（可测） |
|------|------|------------------|
| `checks/base.py` | `Check` 协议（`id`/`title`/`severity`/`run(ctx)`）+ 注册装饰器 | 检查只读；协议被 `runtime_checkable` 校验；新增检查无需改 runner |
| `checks/python_env.py` | 解释器版本、是否 venv、`sys.executable` 脱敏 | 3.11 解释器模拟下产出 `warn`；3.12+ 产出 `ok` |
| `checks/platform_info.py` | OS/版本/架构/控制台编码（cp936 提示） | 在 Windows CI 上断言编码检查存在；Linux 上标记 `skipped` |
| `checks/path_health.py` | PATH 条目存在性、重复项、非 ASCII、超长（>240） | 用 `monkeypatch.setenv("PATH", ...)` 构造 4 种坏 PATH，各产出对应 `warn` |
| `checks/toolchain.py` | `shutil.which` 探测 git/node/npm/uv，**不执行** | 缺失工具 → `warn` 且 message 含安装建议；不产生子进程（断言 `subprocess` 未被调用） |
| `checks/fs_health.py` | 临时目录可写探测、磁盘剩余空间 | 只写 `tempfile` 并在 `finally` 删除；`PermissionError` 模拟下 → `error` 而非崩溃 |
| `checks/longpath.py` | Windows `LongPathsEnabled` 只读检查 | 非 Windows 返回 `skipped`；注册表读取失败降级为 `warn` |
| `services/hashing.py` | 流式 SHA-256，1 MiB 分块 | 空文件、1 B、跨块边界、1 GB 稀疏文件均正确；内存峰值与文件大小无关（用 1 GB 文件测试）；不整文件读入 |
| `services/net.py` | `socket.create_connection(addr, timeout)`，不发应用层数据 | 用本地临时监听端口验证 open；关闭端口验证 refused；不可路由地址验证 timeout；`with` 保证 socket 关闭 |

### 4.4 报告与安全层

| 模块 | 职责 | 验收标准（可测） |
|------|------|------------------|
| `security/paths.py` | 路径规范化、`expanduser`、`resolve`、Windows 保留名与 `\\?\` 前缀处理 | 相对路径基于 CWD 解析；`~` 展开；拒绝写入目录外的 `--output`（路径穿越测试） |
| `security/redact.py` | 脱敏规则引擎（见 §8） | ≥12 条用例；幂等（二次脱敏结果不变）；对非字符串字段不误伤 |
| `report/base.py` | `Exporter` 协议 `render(report) -> str` | 新格式只需新增一个 exporter，不改 runner |
| `report/json_exporter.py` | UTF-8、`ensure_ascii=False`、稳定字段顺序、末尾换行 | 输出可被 `jsonschema` 校验通过；中文不转义 |
| `report/text_exporter.py` | 人类可读摘要 + 建议 | 输出含每项状态与建议；无 ANSI（由 rendering 负责着色） |
| `logging/setup.py` | stderr handler、级别控制、可选文件、敏感值过滤器 | 日志中不出现 `sk-...`/`ghp_...` 等模式（用注入测试断言）；日志不写 stdout，避免污染 `--format json` |

---

## 5. 关键设计决策

| ID | 决策 | 理由 |
|----|------|------|
| D1 | **单一诊断管道**：`check` 与 `report` 共用 `runner.run_diagnostics() -> DiagnosticReport`，只是一个渲染、一个序列化 | 避免两套逻辑漂移；报告天然一致 |
| D2 | **检查失败即数据**：单个检查抛异常被 runner 捕获，转为 `status=error` 的 `CheckResult` | 一个坏检查不该让整份报告失败 |
| D3 | **依赖注入时钟与环境**：`RunContext` 持有 `clock`、`settings` | 报告可复现，golden 测试可行 |
| D4 | **脱敏单一漏斗 + 导出二次扫描** | 第一层在构造报告时脱敏，第二层在 exporter 兜底，防新增字段漏脱敏 |
| D5 | **零写入原则**：唯一写操作是用户显式指定的 `--output` / `--log-file`，以及 `tempfile` 可写性探测（即时删除） | 满足"不修改其他应用核心文件" |
| D6 | **默认不执行子进程**：工具版本探测需显式 `--probe-tool-versions`，且 `shell=False` + 超时 | 首版把攻击面压到最小；默认零进程创建 |
| D7 | **端口探测只做 TCP 握手**，不发送任何应用层字节；非回环地址需 `--allow-non-loopback` | 防止被当成扫描器滥用 |
| D8 | **退出码契约固定**：0/1/2/3（见 §7） | 便于 CI 与脚本判断 |
| D9 | **`schema_version` 独立于包版本** | 报告消费者不被工具版本升级打断 |

---

## 6. 报告结构（`report --format json`）

```json
{
  "schema_version": "1.0",
  "tool": { "name": "agent-doctor", "version": "0.1.0" },
  "generated_at": "2026-10-24T01:32:07Z",
  "environment": {
    "os": "Windows-11-10.0.22631",
    "arch": "AMD64",
    "python": "3.12.7",
    "cwd": "<CWD>",
    "user": "<USER>",
    "hostname": "<HOSTNAME>"
  },
  "summary": { "total": 8, "ok": 5, "warn": 2, "error": 1, "skipped": 0, "duration_ms": 412 },
  "checks": [
    {
      "id": "python.version",
      "title": "Python 版本",
      "status": "ok",
      "severity": "info",
      "message": "Python 3.12.7（满足 >=3.12）",
      "details": { "version": "3.12.7", "executable": "<HOME>\\...\\python.exe" },
      "duration_ms": 1,
      "findings": []
    },
    {
      "id": "path.health",
      "title": "PATH 健康度",
      "status": "warn",
      "severity": "warn",
      "message": "发现 2 个不存在条目、1 个非 ASCII 条目",
      "details": { "entries": 23, "missing": 2, "non_ascii": 1, "duplicated": 0 },
      "duration_ms": 3,
      "findings": [
        { "severity": "warn", "message": "PATH 中存在不存在的目录，可能拖慢命令解析", "suggestion": "在系统环境变量中清理无效条目" }
      ]
    }
  ]
}
```

字段约定：
- 时间统一 UTC ISO-8601（`Z` 结尾，秒精度）
- `details` 只允许 `str | int | float | bool | null`，禁止嵌套对象与数组（便于消费者处理）
- 所有绝对路径都经过脱敏，以 `<HOME>` / `<CWD>` / `<TEMP>` 占位符开头

---

## 7. 退出码与错误处理

| 退出码 | 含义 | 触发示例 |
|--------|------|----------|
| 0 | 成功，未发现达到阈值的问题 | `check` 全 ok/warn |
| 1 | 发现问题达到 `--fail-on` 阈值 | `check --fail-on error` 且存在 error |
| 2 | 用法/输入错误（可预期） | 文件不存在、端口非法、`--output` 目录不存在 |
| 3 | 内部错误（未预期） | 未捕获异常，已记日志到 stderr |

- `check` 默认 `--fail-on error`；`report` 默认 `--fail-on never`（导出命令不应因诊断结果失败）。
- 所有 `OSError` 在 service 层被转换为领域异常，附带用户可读信息与建议；不向用户展示 traceback，除非 `--log-level DEBUG`。
- 任何情况下 **stdout 只输出结果**，诊断信息与错误走 stderr，保证 `report --format json > report.json` 得到干净 JSON。

---

## 8. 脱敏规则

| # | 规则 | 输入示例 | 输出 |
|---|------|----------|------|
| R1 | 用户主目录 | `C:\Users\alice\proj` | `<HOME>\proj` |
| R2 | 当前工作目录 | `C:\Users\alice\proj\src` | `<CWD>\src` |
| R3 | 临时目录 | `C:\Users\alice\AppData\Local\Temp\x` | `<TEMP>\x` |
| R4 | 用户名 | `alice`（出现在路径外） | `<USER>` |
| R5 | 主机名 | `DESKTOP-ABC123` | `<HOSTNAME>` |
| R6 | OpenAI 风格密钥 | `sk-proj-abc...` | `<REDACTED:OPENAI_KEY>` |
| R7 | GitHub token | `ghp_...` / `github_pat_...` | `<REDACTED:GH_TOKEN>` |
| R8 | AWS Access Key | `AKIA...` | `<REDACTED:AWS_KEY>` |
| R9 | Bearer / Authorization | `Bearer eyJ...` | `Bearer <REDACTED>` |
| R10 | 通用 `KEY=value` | `API_KEY=abcd1234` | `API_KEY=<REDACTED>` |
| R11 | 连接串凭据 | `https://u:p@host` | `https://<REDACTED>@host` |
| R12 | 私有绝对路径（非 HOME 盘符路径） | `D:\work\secret\a.txt` | `<ABS_PATH>\a.txt` |

实现要点：正则预编译、按最长匹配优先、单次遍历替换；**幂等**（已含 `<...>` 占位符的片段跳过）。密钥类规则只作用于字符串值，不作用于字段名。

---

## 9. 安全设计（威胁 → 控制）

| 威胁 | 控制措施 | 验证方式 |
|------|----------|----------|
| 自动执行修复命令 | 代码中不存在 `subprocess`/`os.system` 调用（D6 opt-in 除外），建议只以文本输出 | 单测断言默认路径下 `subprocess.run` 未被调用；CI grep 白名单 |
| 上传文件/日志 | 代码中无 HTTP 客户端；唯一网络操作是用户指定的 TCP 探测 | CI 中 `grep -rE "requests|httpx|urllib.request|aiohttp"` 必须为空 |
| 读取/打印密钥 | 不读取环境变量**值**（只判断存在性）；日志过滤器 + 报告脱敏 | 注入假密钥到 env，断言报告与日志中均不出现明文 |
| 报告泄露个人信息 | §8 规则 + 导出二次扫描 | 12 条脱敏用例 + golden 报告断言 |
| 路径穿越 / 误写 | 写操作仅 `--output` / `--log-file`；写入前校验父目录存在且非符号链接；原子替换（临时文件 + `os.replace`） | 路径穿越测试：`--output ../../x` 被拒绝 |
| 修改其他应用核心文件 | 全部检查只读；无注册表写入（`winreg` 仅 `OpenKey` 读） | 代码审查 + 测试用 `tmp_path` 隔离 |
| 权限错误导致崩溃 | service 层捕获 `PermissionError` → `PathError`，退出码 2 | 权限错误测试（见 §10.3） |
| 长路径 / 编码问题 | `pathlib` 全量、显式 UTF-8 写文件、Rich 处理控制台编码 | Windows CI 上跑含中文与空格路径的用例 |

---

## 10. 测试策略

### 10.1 分层

| 层 | 位置 | 关注点 | 是否 mock 外部 |
|----|------|--------|----------------|
| 单元 | `tests/unit/` | 纯逻辑：哈希、脱敏、路径、注册表、runner、exporter | 是（socket/fs） |
| 集成 | `tests/integration/` | 通过 `CliRunner` 走完整命令，断言 stdout/stderr/退出码 | 部分（真实临时文件） |
| 契约 | `tests/contract/` | golden JSON + `jsonschema` 校验报告结构 | 否（fake clock 固定时间） |

### 10.2 必测场景矩阵

| 场景 | 覆盖对象 | 手法 |
|------|----------|------|
| 正常 | 全部命令 | `tmp_path` 真实文件；本地真实监听端口 |
| 失败（业务） | check 单项 error、端口 refused | 构造坏 PATH；关闭端口 |
| 缺失文件 | `hash`、`--output` 父目录 | 不存在的路径 |
| 权限错误 | `hash` 读取、`fs_health` 写入、`--output` 写入 | 见 §10.3 |
| 非法参数 | 端口越界、格式非法、`--only` 未知 id | `CliRunner` 断言退出码 2 |
| 内部异常 | runner 兜底 | 注册一个必抛异常的假检查 |
| 脱敏 | 报告与日志 | 注入假密钥 + 假用户名 |

### 10.3 Windows 下的权限错误测试（重要）

Windows 上 `chmod 000` 不生效，不能照搬 POSIX 写法。采用双轨：

1. **跨平台**：`monkeypatch` 让 `Path.open` / `os.stat` 抛 `PermissionError(13, "Access is denied")`，验证异常映射与退出码 —— 所有平台都跑。
2. **仅 POSIX**：`@pytest.mark.skipif(os.name == "nt")` 的真实 `chmod(0)` 测试，在 Linux CI 上补充真实行为。

### 10.4 覆盖率与门槛

- 全局行覆盖率 ≥ 85%，`agent_doctor/services`、`agent_doctor/security`、`agent_doctor/report` ≥ 95%
- `--cov-fail-under=85` 进 CI
- 禁止 `# pragma: no cover` 出现在业务分支（仅允许在 `if TYPE_CHECKING`）

---

## 11. CI 设计

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, ubuntu-latest]
        python: ["3.12", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python }}" }
      - run: python -m pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest -q --cov=agent_doctor --cov-fail-under=85
  license:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python -m pip install -e ".[dev]"
      # 白名单策略检查 + 清单一致性检查，详见 §2.1
      - run: python scripts/gen_licenses.py --check
```

`pyproject.toml` 关键配置：

```toml
[project]
name = "agent-doctor"
requires-python = ">=3.12"
dependencies = ["typer>=0.27,<1", "rich>=15,<16", "pydantic>=2.14,<3"]

[project.scripts]
agent-doctor = "agent_doctor.cli.app:main"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF", "S", "PL"]
# S = bandit 规则，用静态检查兜住安全要求

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

> `S`（flake8-bandit）与 `B`（bugbear）是刻意加的：把"禁止 subprocess""禁止硬编码密码"这类安全要求变成 CI 可执行的规则，而不是靠人记。

---

## 12. 垂直切片计划

| 切片 | 范围 | 交付物 | 验收 | 预计测试 |
|------|------|--------|------|----------|
| **S1** | 骨架 + `hash` 命令打通全链路 | `pyproject.toml`、`LICENSE`、`.gitignore`、`cli/app.py`、`cli/commands/hash.py`、`services/hashing.py`、`security/paths.py`、`security/redact.py`（基础版）、`core/errors.py`、`logging/setup.py`、`ci.yml`、README | `agent-doctor hash <file>` 输出正确 SHA-256；四类错误退出码正确；CI 双平台绿 | ~28 |
| **S2** | `check` + `report --format json` | `models/*`、`core/registry.py`、`core/runner.py`、`checks/*`（6 个）、`report/*`、`cli/rendering.py` | 报告通过 JSON Schema 校验；golden 测试通过；脱敏生效 | ~45 |
| **S3** | `proxy` | `services/net.py`、`cli/commands/proxy.py` | open/refused/timeout 三态可复现；非回环需显式开关 | ~15 |
| **S4** | 收尾 | `docs/*` 补全、`THIRD_PARTY_LICENSES.md`、`CHANGELOG.md`、`0.1.0` tag | 打包 `python -m build` 成功，wheel 内无多余文件 | ~8 |

**每个切片结束必须报告**：修改的文件清单、`pytest` 实际输出摘要、`ruff` 结果、未解决问题。测试结果一律来自真实执行，不预估。

---

## 13. 待确认问题（请回复编号即可）

1. **包名/仓库名**：`agent-doctor`（PyPI）与 `agent_doctor`（import）是否确认？GitHub 仓库归属（个人/组织）？
2. **依赖管理**：用 `uv` + `uv.lock`（推荐，锁文件可复现），还是纯 `pip` + 版本区间？
3. **`--probe-tool-versions`**：是否保留这个"显式开关才执行 `git --version`"的能力？默认关闭。若不需要，S2 直接不做，攻击面更小。
4. **`check` 的检查项**：当前 6 项（Python/平台/PATH/工具链/文件系统/长路径）是否够，是否要加"环境变量里是否存在 `OPENAI_API_KEY` 等键名"（只报存在性，不读值）？
5. **`report` 默认格式**：`json`（按你的示例）还是 `text`？
6. **`report --output` 已存在文件**：默认拒绝并提示，还是自动覆盖（`--force` 才覆盖）？我倾向拒绝。
7. **是否加 mypy**（`--strict` 子集）？我建议加，成本低、对"可维护"收益大，但会加一条 CI 门槛。
8. **许可证署名**：`Copyright (c) 2026 <你的名字或组织>`，请给出署名文本。

确认后我立即开始 S1，只做 `hash` 这一条垂直切片，不做其他命令。

---

## 14. 阶段二实施记录（与 v0.1 设计的差异）

阶段二的需求把"诊断结果模型"的字段和状态取值定死了，与本文档 §4.2、§6 的初版设计不同。
按"对已有工作影响最小"的原则处理：**需求优先，文档补记**，不推翻 §1–§13 的分析。

| # | v0.1 设计 | 实际实现 | 原因 |
|---|-----------|----------|------|
| 1 | `Status = ok / warn / error / skipped` | `Status = pass / warn / fail / info` | 阶段二需求明确指定；四个值一一对应，无信息损失 |
| 2 | `CheckResult(id, title, message, severity, duration_ms, findings)` | `CheckResult(name, status, summary, details, recommendation)` | 需求指定字段；`severity` 与 `status` 语义重叠，去掉一层 |
| 3 | `details` 允许嵌套对象 | 只允许 `str / bool / int / float / null` | 消费者处理更简单，也顺手挡掉了"把文件内容塞进报告"这类误用 |
| 4 | `agent-doctor report --format json` | 已实现（`--format json\|text`、`--output` 原子写入、默认拒绝覆盖），另三个命令也支持 `--json` | 阶段二先用 `--json` 打通导出器，阶段三补上独立命令，导出器完全复用 |
| 5 | `checks/base.py` 放 Check 协议 | 合并进 `core/registry.py` | 只有 30 行，单独开文件反而增加跳转成本 |
| 6 | `logging/setup.py` | `logging_setup.py` | 包内出现名为 `logging` 的子包容易和标准库混淆 |
| 7 | `models/settings.py` + pydantic-settings | 未实现，依赖未引入 | 当前没有任何可配置项；"不新增不必要的依赖"优先 |
| 8 | 6 个检查项 | 注册 7 个，默认执行 6 个（Python / 平台 / PATH / 工具链 / 文件系统 / 长路径）；`toolchain.versions` 需显式开关 | 阶段二先做 4 个打通管道，阶段三补齐后两个，阶段四加版本探测 |
| 9 | `--probe-tool-versions` 显式开关 | 已实现（`check` 与 `report` 均支持） | 见 §15；默认零子进程的约束保持不变 |
| 10 | 全局 `--no-color` | 未实现，依赖 Rich 的非 TTY 自动降级与 `NO_COLOR` | 少一个全局选项，行为已经满足"管道输出不带 ANSI" |

`report/text_exporter.py` 同理未单独建文件：人类可读输出由 `cli/rendering.py` 承担，
它依赖 Rich，属于表现层，不该放进 `report/`。


---

## 15. 工具版本探测（阶段四新增）

默认**不执行任何外部程序**。`--probe-tool-versions` 是显式开关；未开启时
`toolchain.versions` 根本不会进入本次运行——不是"执行了再忽略结果"。

### 15.1 门禁机制

检查项在注册时带 `requires_probe=True` 标记：

```python
@check("toolchain.versions", "工具版本", requires_probe=True)
```

`select(names, probe_versions=False)` 过滤掉带标记的项，`run_checks()` 默认
`probe_versions=False`。因此默认路径的子进程数量恒为 0，由
`test_default_check_creates_no_subprocess` 直接断言（替换 `subprocess.run`
后断言调用次数为 0）。

若用户显式 `--only toolchain.versions` 却没开开关，返回 `UsageError`（退出码 2）
并提示需要同时传入开关，而不是静默跳过。

### 15.2 执行约束

| 约束 | 实现 |
|------|------|
| 不经 shell | `shell=False`，参数是 `[exe, "--version"]` 固定列表 |
| 可执行文件可信 | 路径来自 `shutil.which()`，不是用户输入 |
| 不挂死 | `timeout=10s` |
| 不等待输入 | `stdin=subprocess.DEVNULL` |
| 不灌爆报告 | 只取 stdout 首行，版本串截断到 64 字符 |
| 不泄漏路径 | `OSError` 只记录 `类型: strerror`，不含可执行文件路径 |

### 15.3 结果分类

`ProbeOutcome` 取值为 `ok` / `not_found` / `failed`（非零退出）/ `timeout` /
`error`（OSError）。

状态判定刻意与 `toolchain.presence` 分工，避免同一问题报两次：

- `not_found`（不在 PATH）→ 记"未安装"，**不**让本项告警；
- 全部 `not_found` → `info`，没有可探测的对象；
- 有 `failed` / `timeout` / `error` → `warn`，summary 点出具体工具。

### 15.4 超时取值依据

初版设 3 秒。实测在本机 Windows 上首次运行 `check --probe-tool-versions`
时 `npm` 被误判超时；单独计时 `npm --version` 稳定在 1.5 秒左右，属冷启动
（Node 首次加载模块 + 杀毒软件扫描）。放宽到 **10 秒**。诊断工具误报"探测
失败"会把用户引向错误的排查方向，代价高于多等几秒。
