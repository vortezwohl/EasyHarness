# Subdesign: D-002-typed-signal-projector

## Metadata
- Document Type: Design
- Document ID: D-002
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Concept
- Canonical Name: Adapter plus explicit finite phase lifecycle
- Category: Structural Adapter and explicit finite-state lifecycle
- Reference: GoF Adapter; Strands 1.45 reasoning stream normalization.

## Intent
将 Strands 原始事件、工具 marker、压缩回调与公开协议隔离。

## Stable Core and Variation
- 稳定：私有 signal 到公开事件的投影、phase 生命周期、sequence 分配。
- 变化：Strands 原始事件、工具结果和压缩载荷。

## Repository Evidence
- 当前 `_EventMapper.feed()` 混合解析 `reasoningText`、`data`、`result`、工具 marker 和压缩字典。
- 工具以 tool-use ID 关联且可并发；chunks 只为终态全文而存在。

## Compatibility Boundary
只暴露新公开事件。内部工具和压缩 marker 改为私有强类型 signal，不保留魔法字典协议。

## Pattern Decision
- 选择 Adapter：来源只产出私有 signal，投影器不读取 Strands 原始 key。
- 拒绝 State 类层级：状态有限固定，显式转移表优于继承。
- 拒绝其余 GoF 模式：没有独立算法族、创建、树、撤销、广播或持久化需求。

## External Evidence Decision
采纳 Adapter 的边界翻译职责；拒绝 CEP 和事件溯源架构，因为 EasyHarness 是同步迭代 SDK。

## Rationale
分开来源适配和公共投影，消除文本重复和全文累计内存。

## Alternatives
仅禁止 `_flush_thinking()` 发 text 被拒绝：assistant 和非类型化来源边界仍有问题。

## Functional Boundary
- 文本 phase 为 started、零或多次 delta、一个 completed/failed/cancelled。
- 有 assistant delta 时忽略 result 重复全文；无 delta 时只补发一次 fallback delta。
- thinking 不从 result 生成快照；取消/失败终结所有活动 phase，工具仍按 tool-use ID 关联。

## Code Impact Scope
- `runtime.py`、`conversation.py`、`tools.py`、必要的私有流模块和 `tests/test_sdk.py`。

## Verification Seams
reasoning 后工具、工具后 reasoning、assistant、fallback、取消、异常、并发工具、压缩失败和无效载荷。

## Counterexamples
断线重连全文快照只能是独立 replay API，不能回填到实时 completed。

## Anti-Patterns
前端去重、字符串前缀去重、result 覆盖 delta、Strands key 泄漏到公开 API。

## Rules
### MUST DO
- R-D002-001: sequence 只由单个投影器递增，phase_id 只由 phase registry 分配。
- R-D002-002: 所有终态经同一个 `finish_phase()` 发射。

### MUST NOT DO
- R-D002-N001: 不存储完整文本，只记录 phase 是否已发送文本 delta。
- R-D002-N002: 不让 Strands 原始 key 出现在公开类型或 README。
