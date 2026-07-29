# Subdesign: D-001-canonical-stream-contract

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Concept
- Canonical Name: Append-only phase event contract
- Category: Public protocol
- Reference: Cugola and Margara, *Processing Flows of Information*, ACM CSUR 2012, DOI `10.1145/2379776.2379781`

## Intent
为所有调用方建立唯一、可顺序消费、不可歧义的流式事件语义。

## Stable Core and Variation
- 稳定：phase 生命周期、事件顺序、文本增量的追加语义。
- 变化：上游模型事件格式、工具和压缩的内部来源。

## Repository Evidence
- `runtime.py` 的 `_flush_thinking()`、`_flush_assistant()` 累计 chunks 后在终态回填全文。
- `types.py` 的 `AgentEvent.text` 未区分快照与增量。
- 复现输入 `A`、`B` 得到两个 delta 后一个 `completed AB`。

## Compatibility Boundary
破坏性替换；移除 `status`、`text`、`name` 和 schema/版本兼容字段。新事件必须有 `sequence`、`phase_id`、`kind`、`operation`；调用方仅在 `operation == "delta"` 时追加 `delta`。

## Pattern Decision
- 选择：无 GoF 公共对象模式；公开协议必须平坦、可序列化且不隐藏语义。
- 拒绝：Observer，因为 `stream()` 是单消费者有序迭代；Command、Memento、Event Sourcing 会错误增加持久化/回放职责。

## External Evidence Decision
采纳事件流应区分事件事实与消费者派生状态的原则；参考 Microsoft Event Sourcing 的 append-only 事实说明，但明确拒绝持久化、重放和事件存储。

## Rationale
phase 完成是生命周期事实，累计文本是消费者可派生状态；二者不能共享一个文本字段。

## Alternatives
保留 `text` 并规定 completed 为快照被拒绝：每个消费者必须分支处理，仍会重新引入错误拼接。

## Functional Boundary
- 改变：公开 `AgentEvent` 字段和消费语义。
- 保护：工具执行、取消、失败、压缩和单 Agent 串行调用。
- 非目标：模型供应商适配、会话历史、前端渲染。
- Hard-stop：若存在不能改造的外部 SDK 消费者，停止，不恢复兼容字段。

## Code Impact Scope
- `easyharness/_internal/types.py`、`easyharness/_internal/runtime.py`、`tests/test_sdk.py`、`README.md`、`easyharness/__init__.py`。

## Verification Seams
连续 sequence；同 phase 的 phase_id 一致；每个文本字符只出现一次；终态无 delta；failed 只经 error 表达。

## Counterexamples
没有上游 assistant delta 但 result 有最终文本时，必须补发一次 assistant delta 后再完成。

## Anti-Patterns
在 completed 重放全文；新增 `schema_version`、`isV2` 或旧字段别名；让调用方猜测字段含义。

## Rules
### MUST DO
- R-D001-001: 对 operation、delta、error 和终态字段组合做类型级校验。
- R-D001-002: README 只给出一种消费循环：仅追加 `event.delta`。

### MUST NOT DO
- R-D001-N001: 不累计文本后再次向公开流发射。
- R-D001-N002: 不保留旧字段别名、运行期兼容开关或双协议。
