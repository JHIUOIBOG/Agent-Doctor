# Agent Doctor

面向 Windows 开发者的**本地** AI 编程环境诊断工具。只读、离线、不自动修复。

```text
agent-doctor check
agent-doctor proxy --host 127.0.0.1 --port 65532
agent-doctor hash <path> [--expected <sha256>]
agent-doctor report --format json
```

## 安装

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev]"
```

## 命令

### `check` — 基础环境检查

默认运行 6 个只读检查项，输出表格。

| 检查项 | 说明 |
|--------|------|
| `python.version` | 解释器版本、是否在虚拟环境 |
| `platform.info` | 系统 / 架构 / 控制台编码（cp936 会提示） |
| `path.health` | PATH 中不存在、重复、非 ASCII、超长条目 |
| `toolchain.presence` | git / node / npm / uv 是否存在（只查 `shutil.which`，不执行） |
| `toolchain.versions` | 工具版本，**需 `--probe-tool-versions`**，会执行 `--version` |
| `fs.health` | 临时目录可写性、剩余磁盘空间 |
| `windows.longpath` | 长路径支持是否启用（只读注册表） |

```bash
agent-doctor check
agent-doctor check --json      # 机器可读
agent-doctor check --only python.version --only fs.health
agent-doctor check --probe-tool-versions   # 显式开启版本探测
```

**默认零子进程**：不开 `--probe-tool-versions` 时，`toolchain.versions` 根本不会
进入本次运行，本工具不会启动任何外部程序。开启后以 `shell=False`、固定参数、
10 秒超时、`stdin=DEVNULL` 的方式调用 `git/node/npm/uv --version`，只取版本号。
详见 [`docs/DESIGN.md`](docs/DESIGN.md) §15。

### `report` — 导出诊断报告

```bash
agent-doctor report                              # JSON 到 stdout
agent-doctor report --format text                # 纯文本，适合贴进 issue
agent-doctor report --output report.json         # 写文件（已存在则拒绝）
agent-doctor report --output report.json --force # 覆盖
```

写入采用"临时文件 + `os.replace`"的原子替换，中途失败不会留下半个 JSON。
报告在落盘前完成脱敏。

报告字段契约见 [`docs/REPORT_SCHEMA.md`](docs/REPORT_SCHEMA.md)，
字节级样例见 [`tests/contract/golden/report.json`](tests/contract/golden/report.json)。

### `proxy` — 本地端口连通性

只做 TCP 握手，不发送任何应用层数据。

```bash
agent-doctor proxy --host 127.0.0.1 --port 65532
agent-doctor proxy --host 127.0.0.1 --port 65532 --timeout 1.5 --json
```

默认只允许回环地址（`127.0.0.1`、`::1`、`localhost`）。要探测其他主机必须显式加
`--allow-non-loopback`，避免这个工具被当成端口扫描器使用。

### `hash` — 文件 SHA-256

流式读取，内存占用与文件大小无关。不修改、不移动被检查的文件。

```bash
agent-doctor hash .\dist\agent-doctor-0.1.0-py3-none-any.whl
agent-doctor hash .\a.bin --expected 3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b
```

## 退出码

| 码 | 含义 |
|----|------|
| 0 | 正常（`check` 无 fail；`hash` 匹配；`proxy` 连接成功） |
| 1 | 诊断发现问题（`check` 有 fail；`hash` 不匹配；`proxy` 拒绝/超时） |
| 2 | 用法或输入错误（路径不存在、端口非法、哈希格式错误） |
| 3 | 内部错误（已记录到 stderr，不会把 traceback 喷到 stdout） |

## 安全边界

- **不执行**任何修复命令，也不创建子进程（工具版本探测仅用 `shutil.which`）。
- **不上传**任何文件、日志或报告；唯一的网络行为是用户指定的 TCP 握手。
- **不读取** API 密钥；报告中的主目录、临时目录、用户名、主机名会被替换为 `<HOME>` / `<TEMP>` / `<USER>` / `<HOSTNAME>`。
- 被检查的文件**只读打开**，不会修改、覆盖或删除。

## 开发

```bash
ruff check .
ruff format --check .
pytest -q
python scripts/gen_licenses.py --check   # 许可证白名单 + 依赖清单是否过期
```

新增或升级依赖后，需重新生成许可证清单并一并提交：

```bash
python scripts/gen_licenses.py
```

设计说明见 [`docs/DESIGN.md`](docs/DESIGN.md)，依赖许可证清单见
[`docs/THIRD_PARTY_LICENSES.md`](docs/THIRD_PARTY_LICENSES.md)。

## 许可证

MIT
