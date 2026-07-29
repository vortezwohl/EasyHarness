# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Observed Facts
- `_EventMapper` 对同一 thinking phase 发出逐段 delta，并在 `_flush_thinking()` 以 `"".join(chunks)` 发出 completed 全文。
- 实测序列为 `started None`、`delta A`、`delta B`、`completed AB`；追加型消费者必然重复。
- assistant 也累计 chunks 并在 `_flush_assistant()` 回填 result 文本，具有同类风险。
- 此语义自提交 `ce9ed758` 存在；`cf9ff5b` 未改变它。现有 50 项测试通过但未覆盖 reasoning 文本序列。
- 当前依赖为 `strands-agents 1.45.0` 与 `litellm 1.89.3`；Strands 将 provider reasoning delta 规整为 `reasoningText`。

## Approved Input Limits
- 只执行 D-001、D-002；不新增持久化事件系统、版本协商或旧协议适配。

## Compatibility Intent
- 用户明确允许破坏性重构。所有消费者迁移到新协议；没有旧字段、schema 版本标记或迁移义务。

## Functional Boundary
- Requested Functionality: 文本只经 delta 一次发送；每个事件有连续 sequence 和稳定 phase_id；终态只表达生命周期。
- Protected Functionality: 单次调用互斥、工具 use ID 关联、取消、失败、压缩、run 最终文本和模型历史。
- Explicit Non-Goals: 前端、provider 请求参数、会话存储、多版本协议。
- Compatibility Guarantees: 只保证新协议自洽，不保证旧 AgentEvent 属性可用。
- Mandatory Stop Condition: 若必须保留旧字段、为不可改造消费者增加双协议，或改变受保护行为，必须停止并请求裁决。

## Preserved Contracts
- `Agent.run()` 最终文本和取消后的可复用性。
- `Agent.stream()` 同步迭代、工具输入输出结构及取消/失败行为。

## Explicitly Permitted Contract Changes
- `AgentEvent` 字段、operation 名称、事件数据位置、README 示例和依赖旧字段的 SDK 测试。
- 私有压缩/工具 marker 可替换为强类型 signal。

## Execution Constraints
- 验证使用 `D:\github-project\EasyHarness\.venv`；用户给出的 `D:\github-project\EasyHarness.venv` 缺少目录分隔符。
- 新/改 Python 文件保持 UTF-8 without BOM、项目 Ruff 规则和项目中文注释要求。
