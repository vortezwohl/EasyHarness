## Why

EasyHarness 当前的工具事件映射器只维护一个全局“当前工具阶段”槽位。当两个工具阶段发生重叠时，后到达的 `started` 会覆盖先前状态，导致后续 `completed` 或 `failed` 终态被错误绑定到新的 `tool_use_id`、`name`、`input` 与计时信息上。这个问题已经不只是 TUI 呈现错误，而是 SDK 公开 `AgentEvent` 契约本身会产出错误事件序列。

现在修复这件事是必要的，因为 EasyHarness 的核心价值之一就是向上层输出稳定、可归约的统一事件流。如果公开事件流不能在工具重叠场景下保持身份一致性，任何基于 `tool_use_id` 做时间线归并、状态收口或调试展示的上层消费方都会得到错误结果。

## What Changes

- 修正 runtime 工具事件映射逻辑，使工具终态按原始 `tool_use_id` 精确关联，而不是依赖单个全局活动工具槽位。
- 明确公开事件流契约：工具 `started`、`completed`、`failed`、`cancelled` 事件必须在同一次工具调用内保持一致的身份字段，包括 `tool_use_id`、`name`、`input`、`started_at` 与持续时间来源。
- 补充覆盖重叠工具阶段的最小回归测试，验证同名工具和异名工具场景都不会发生终态串线。
- 不新增公开顶层导出，不引入新依赖，也不把这个修复扩展成新的并发 runtime 模型。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtime-event-stream`: 补充并收紧工具事件身份一致性要求，确保公开 `AgentEvent` 在工具阶段重叠时仍然稳定且可正确归约。

## Impact

- 受影响代码集中在 `easyharness/_internal/runtime.py` 的 `_EventMapper` 工具阶段状态管理逻辑。
- 受影响测试主要位于 `tests/test_sdk.py`，需要新增工具阶段重叠的回归测试，并验证公开事件序列与字段关联关系。
- 这次变更不会引入新的公开类型、第三方依赖或新的顶层 API，但会收紧 `agent.stream(...)` 的公开正确性契约。
