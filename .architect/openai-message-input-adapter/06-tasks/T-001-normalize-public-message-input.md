# Task: T-001-normalize-public-message-input

## Metadata
- Document Type: Task
- Document ID: T-001
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-002, R-D001-003, R-D001-004, R-D001-N001, R-D001-N002, R-D001-N003
- Prohibited New Concepts: 多模态 Adapter、Responses API Adapter、会话替换、工具重放或可插拔转换策略。

## Preconditions
确认当前 `runtime.py` 的 Strands 调用入口和 Strands 1.45.0 的 `Messages`、`ToolUse`、`ToolResult` 结构；工作区无本计划外的冲突性改动。

## Functional Boundary
- Requested Functionality: 在 `runtime.py` 中将 `str | list[dict]` 规范化为 Strands `Messages`，并让 run/stream 使用同一结果。
- Protected Functionality: 字符串 API、历史追加、系统提示、Context、取消、压缩、事件与单会话占用。
- Explicit Non-Goals: 多模态、Responses API、历史替换、历史工具执行和 provider 专有 reasoning。
- Compatibility Guarantees: 原字符串调用的结果和运行生命周期不变；列表规范化后追加到现有历史。
- Mandatory Stop Condition: 需要接受/拼接系统角色、静默忽略结构或改变会话追加时停止。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/runtime.py` | 私有输入规范化函数、`_StrandsRuntime.run` / `stream`、`Agent.run` / `stream` | 声明联合输入类型，严格转换文本、assistant tool_calls 和 tool result，并在进入 Strands 前调用。 | 当前输入边界和两个执行路径均在此模块。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 只有运行时拥有公开输入与底层 Strands 调用之间的边界。
- Scope Expansion Decision Rule: 仅当可验证的 Strands 类型或现有运行路径要求相邻运行时代码配合，且不改变 D-001 功能边界时才扩展。
- Required Assessment and Record: 记录新增路径、触发证据、是否影响受保护功能、最小设计与新增验证。

## MUST DO
- M-T001-001: 使用一个无状态私有函数处理两种输入，创建新 `Messages`，并用索引/字段路径报告错误。
- M-T001-002: 将 OpenAI assistant `tool_calls` 映射为 `toolUse`，将 OpenAI tool 映射为含 `toolResult` 的 Strands user 消息。
- M-T001-003: 将 JSON arguments 解码为 object；失败时在模型调用前抛出 `ValueError`。

## MUST NOT DO
- N-T001-001: 不得在 run/stream 复制转换代码，不得修改调用方输入。
- N-T001-002: 不得接受 `system`、`developer`、不支持 role 或字段，不得让其静默丢失。
- N-T001-003: 不得触碰工具执行、模型格式化或会话管理的业务逻辑，除非发生已记录且不越界的运行时约束。

## Atomic Steps
1. 阅读并确认当前运行时签名、Strands 消息类型与已有测试替身。
2. 在运行时定义私有联合输入类型和严格规范化函数，覆盖字符串、user、assistant 文本/函数调用和 tool 结果。
3. 更新私有与公共 run/stream 签名、docstring 和调用点，使其只向 Strands 传入 `Messages`。
4. 运行最小导入或语法检查；将行为验证留给 T-002 的完整回归组。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 已批准映射无法在 Strands `Messages` 中表达，或必须改变系统提示/会话追加/工具历史语义。
- Required Conflict Analysis: 列出输入样例、Strands 类型约束、受影响的受保护功能、最小兼容替代和验证影响。
- Recommended Option: `1` 严格拒绝该不兼容输入并保留 D-001 已批准的文本/function-tool 子集。
- Recommendation Rationale: 严格失败可防止历史被静默损坏，并保持系统提示与会话所有权。
- Decision Prompt: 请选择 `1` 保持严格子集，或 `2` 批准扩展一个明确的新输入契约。
- Decision Limit: 仅决定当前无法表达的输入类别；不得顺带批准多模态、会话替换或工具重放。
- Required Decision Record: 在 `08-execution-log.md` 和 `.state/execution-state.json` 记录冲突、选项、用户决定、影响路径和验证结果。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 严格拒绝无法表达的输入 | 完成已批准的文本/function-tool 子集。 | 完全保留系统提示和会话语义。 | 新类别保持 `ValueError`。 | 断言失败早于模型调用且 Agent 可复用。 |
| 2 | 由用户批准新的专门设计 | 当前任务停止，后续进入新设计。 | 可能扩大受保护面的评估范围。 | 需明示新 API 及迁移影响。 | 新设计定义对应的契约和回归组。 |

## Required Verification Evidence
- Verification Procedure: 对改动模块执行语法/导入检查，并由 T-002 运行 SDK 回归测试。
- Required Evidence: 运行时代码仅向 Strands 调用传递 `Messages`，且没有未处理 placeholder、编码或类型错误。

## Completion Criteria
共享规范化边界已接入 public/private run/stream；所有批准输入和拒绝条件均可由 T-002 进行行为断言，且没有跨越 D-001 非目标。
