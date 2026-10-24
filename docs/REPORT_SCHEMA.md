# 报告结构说明（schema 1.0）

`agent-doctor report --format json` 的输出契约。字节级样例见
[`tests/contract/golden/report.json`](../tests/contract/golden/report.json)，
该文件由契约测试逐字节比对，改动结构会导致 CI 失败。

## 版本策略

`schema_version` **独立于包版本**。工具升级（0.1.0 → 0.2.0）通常不改 `schema_version`；
只有出现不兼容变更（删字段、改字段语义、改类型）时才提升它，并在 `CHANGELOG.md` 记录。

| 变更类型 | 是否提升 `schema_version` |
|----------|---------------------------|
| 新增可选字段 | 否（消费方应忽略未知字段） |
| 新增 `status` 取值 | 是 |
| 重命名字段 / 改类型 / 删除字段 | 是 |

## 顶层结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `schema_version` | string | 当前固定为 `"1.0"` |
| `tool` | object | `{"name": "agent-doctor", "version": "<包版本>"}` |
| `generated_at` | string | UTC ISO-8601，`Z` 结尾，秒精度 |
| `results` | array | 诊断结果列表，顺序即检查项注册顺序 |
| `summary` | object | 由 `results` 自动统计，不接受外部赋值 |

## `results[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 检查项标识，如 `python.version`、`file.hash`、`proxy.tcp` |
| `status` | string | 见下表，仅四个取值 |
| `summary` | string | 一句话结论，直接面向用户 |
| `details` | object | **扁平**键值对；值只能是 string / boolean / integer / number / null |
| `recommendation` | string \| null | 可选建议，纯文本，永不自动执行 |

`details` 里出现嵌套对象或数组属于契约违规——这条由
`test_details_values_are_flat_scalars` 守住。这样做的原因是：消费方（CI 脚本、工单系统）
不需要递归解析，也顺手挡住了"把文件内容塞进报告"这类误用。

## `summary`

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | integer | `results` 长度 |
| `passed` | integer | `status == "pass"` 的数量 |
| `warnings` | integer | `status == "warn"` 的数量 |
| `failures` | integer | `status == "fail"` 的数量 |
| `info` | integer | `status == "info"` 的数量 |

## `status` 语义

| 取值 | 含义 | 对退出码的影响 |
|------|------|----------------|
| `pass` | 检查通过 | 无 |
| `warn` | 可以继续，但有隐患 | 无 |
| `fail` | 明确不可用，或与期望值不符 | `check` / `hash` / `proxy` 退出码 1 |
| `info` | 纯信息，或该平台不适用 | 无 |

## 脱敏保证

报告在**序列化前**对结构化数据脱敏（不是对 JSON 字符串做替换，否则会被 `\\` 转义绕过）：

| 内容 | 替换为 |
|------|--------|
| 用户主目录 | `<HOME>` |
| 系统临时目录 | `<TEMP>` |
| 当前工作目录 | `<CWD>` |
| OpenAI / GitHub / AWS 密钥、Bearer token | `<REDACTED:...>` 或 `<REDACTED>` |
| `KEY=value` 形式的凭据 | `KEY=<REDACTED>` |
| URL 中的 `user:password@` | `<REDACTED>@` |

脱敏是幂等的：对已脱敏文本再次处理结果不变。

## 完整示例

见 [`tests/contract/golden/report.json`](../tests/contract/golden/report.json)。

## 消费建议

```bash
agent-doctor report --format json > report.json

# 只看失败项
jq '.results[] | select(.status == "fail")' report.json

# 在 CI 里按失败数决定是否中断（注意 report 自身总是 exit 0）
jq -e '.summary.failures == 0' report.json
```
