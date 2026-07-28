# Task: T-001-relax-message-adapter

## Metadata
- Document Type: Task
- Document ID: T-001
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-002, R-D001-003, R-D001-004, R-D001-N001, R-D001-N002, R-D001-N003
- Prohibited New Concepts: 多模态 Adapter、Responses API Adapter、会话替换、历史工具重放、可插拔转换策略。

## Preconditions
确认 runtime.py 输入入口、Strands Messages/ContentBlock 类型和 FakeModel 捕获路径；工作区没有冲突改动。

## Functional Boundary
- Requested Functionality: 将 str 或宽松 OpenAI/provider 文本与工具历史转换为 Strands Messages。
- Protected Functionality: 字符串生命周期、system_prompt、会话追加、工具 Context、事件、取消和单会话占用。
- Explicit Non-Goals: system/developer、多模态、Responses API、会话替换、历史工具执行、跨消息配对。
- Compatibility Guarantees: 字符串行为不变；列表只追加；可映射 metadata 不再因未知字段失败。
- Mandatory Stop Condition: 需要覆盖 system_prompt、静默丢弃不可映射内容或改变会话追加时停止。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/runtime.py | PromptInput, _normalize_prompt, run, stream | 统一转换、放宽 metadata、支持文本 parts/reasoning 映射并保留核心错误。 | 唯一公开消息边界。 |
| tests/test_sdk.py | FakeModel message capture | 添加最小输入边界断言。 | 可离线观察传入 Strands 的对象。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 运行时拥有公开输入与 Strands 调用之间的唯一边界。
- Scope Expansion Decision Rule: 只有现有 reasoning 路径的可验证契约要求时，才可最小扩展到 model.py；不得扩展为 provider 重构。
- Required Assessment and Record: 记录路径、触发证据、受保护功能影响、最小设计与验证。

## MUST DO
- M-T001-001: 使用一个无状态私有 Adapter 创建新的 Messages。
- M-T001-002: 接受可映射 metadata 与文本 parts，保留 assistant tool call、tool result 和可安全表达的 reasoning。
- M-T001-003: 对核心错误在模型调用前给出英文、索引与字段路径明确的 ValueError。

## MUST NOT DO
- N-T001-001: 不得接受、合并或静默忽略 system、developer。
- N-T001-002: 不得静默丢弃媒体或其他不可表达内容。
- N-T001-003: 不得在 run/stream 分别复制逻辑，或加入跨消息语义校验。

## Atomic Steps
1. 复核 Strands 内容类型与当前失败条件。
2. 在 runtime.py 完成最小转换和公开类型/docstring 调整。
3. 为允许与拒绝情形增加离线回归。
4. 运行本任务定向测试并记录结果。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 已请求输入无法表示，且严格失败会违背批准功能。
- Required Conflict Analysis: 展示样例、目标限制、受保护功能影响、最小替代和验证差异。
- Recommended Option: `1`。
- Recommendation Rationale: 严格失败不会静默损坏历史，也不扩大未经批准的契约。
- Decision Prompt: 请选择 `1` 保持严格拒绝，或 `2` 为该输入类别发起新设计。
- Decision Limit: 仅决定当前不可表达类别，不得捆绑批准其他功能。
- Required Decision Record: 在执行日志和状态记录样例、决定、影响和验证。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 严格拒绝该输入 | 保持批准的可映射子集。 | 保留所有受保护语义。 | 新类别继续 ValueError。 | 断言模型调用前失败且 Agent 可复用。 |
| 2 | 用户批准专门设计 | 当前任务停止。 | 重新评估影响。 | 新契约和迁移显式定义。 | 新设计定义完整回归组。 |

## Required Verification Evidence
- Verification Procedure: 运行定向消息测试并检查 FakeModel 捕获的 Messages。
- Required Evidence: 允许字段完成映射、拒绝字段提前失败、输入未变、run/stream 对称。

## Completion Criteria
消息适配只保留最小核心校验，批准输入和错误边界均有离线测试，且没有跨越 D-001 非目标。
