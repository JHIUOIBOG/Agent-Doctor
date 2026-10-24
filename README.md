# Agent Doctor

面向 Windows 开发者的**本地** AI 编程环境诊断工具。只读、离线、不自动修复。

```text
agent-doctor check
agent-doctor proxy --host 127.0.0.1 --port 65532
agent-doctor hash <path> [--expected <sha256>]
```

## 安装

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev]"
```

## 命令

### `check` — 基础环境检查

运行只读检查项（Python 版本、平台信息、PATH 健康度、工具链存在性），输出表格。

```bash
agent-doctor check
agent-doctor check --json      # 机器可读
```

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
```

设计说明见 [`docs/DESIGN.md`](docs/DESIGN.md)。

## 许可证

MIT
