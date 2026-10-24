# Changelog

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.0] - 2026-10-24

### 新增

- `agent-doctor check`：6 个只读检查项（Python 版本、平台与控制台编码、PATH 健康度、工具链存在性、文件系统、Windows 长路径）
- `agent-doctor proxy`：TCP 端口连通性探测，只做握手不发数据；默认仅允许回环地址
- `agent-doctor hash`：流式 SHA-256，支持 `--expected` 比对
- `agent-doctor report`：导出 JSON / 纯文本报告，`--output` 原子写入，默认拒绝覆盖
- 四个命令均支持 `--json`（`report` 为默认格式），输出前对路径与凭据脱敏
- 统一诊断结果模型（`name / status / summary / details / recommendation`）与聚合报告
- 退出码契约：0 正常 / 1 诊断问题 / 2 用法或输入错误 / 3 内部错误
- 185 条 pytest 用例，覆盖正常、失败、缺失文件、权限错误与退出码
- GitHub Actions：Windows + Ubuntu × Python 3.12 + 3.13

### 安全

- 不执行任何外部命令，不创建子进程
- 不上传文件、日志或报告
- 不读取 API 密钥；报告输出前脱敏主目录、临时目录与常见凭据模式
- 被检查文件只读打开，不修改、不移动、不删除
