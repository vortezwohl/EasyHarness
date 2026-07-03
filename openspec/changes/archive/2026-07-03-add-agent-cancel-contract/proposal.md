## Why

EasyHarness 底层依赖的 Strands 已经支持取消进行中的 agent invocation，但 SDK 公开层目前既没有显式 `cancel()` 控制入口，也没有把“取消”建模成稳定的公开事件语义。对于上层 UI 来说，这会直接导致状态机不完整：界面可以展示流式输出，却无法用统一契约表达“用户主动停止了这次运行”，只能把取消误判为完成、失败或前端单侧中断。

现在补齐这块边界是合适的，因为 EasyHarness 的核心卖点本来就是“极简公开表面 + 统一事件流”。如果继续只暴露底层流式能力而不暴露取消契约，后续 TUI、WebUI 和其他运行时消费者都要各自发明一套停止语义，SDK 的统一性会在最基础的交互场景上失效。

## What Changes

- 为公开 `Agent` 增加显式取消当前进行中 invocation 的控制能力，调用方无需下沉到内部 runtime 或底层 Strands 对象。
- 把“取消”定义为 SDK 公开运行时契约中的一等终态，而不是把取消伪装成 `completed` 或 `failed`。
- 调整 `agent.stream(...)` 的公开事件语义，使当前活跃阶段在被取消时发出明确的 `cancelled` 终态，并由系统终态事件统一收口整次 invocation 的停止原因。
- 保持 `run(prompt)` 作为简洁同步入口，但明确 `stream(prompt)` 才是上层 UI 获取完整停止原因和阶段状态的权威接口。
- 保持现有五个顶层公开名字不变；这次变更扩展的是 `Agent` 的实例能力和 `AgentEvent` 的语义，而不是新增并行入口。

## Capabilities

### New Capabilities

- `agent-cancellation`: 定义 EasyHarness 如何公开取消当前 invocation、取消的幂等性与复用语义，以及取消后的公开运行时行为。

### Modified Capabilities

- `agent-sdk-surface`: `Agent` 的公开运行时接口将新增显式取消能力，SDK 公开表面需要把取消纳入标准使用路径。
- `runtime-event-stream`: 公开 `AgentEvent` 终态语义将从仅有 `started` / `delta` / `completed` / `failed` 扩展为覆盖取消场景的稳定契约。

## Impact

- 受影响代码主要位于 `easyharness/_internal/runtime.py` 和 `easyharness/_internal/types.py`，因为这次改动涉及 `Agent` 公开方法、内部 runtime 桥接和 `AgentEvent` 状态枚举。
- 测试需要补充取消进行中的 `stream()`、取消后 Agent 复用、取消阶段终态语义和最终系统收口事件验证，避免 SDK 把取消回退成不透明字符串或隐式完成。
- README 与示例文档需要新增取消控制说明，明确 `stream()` 是 UI 级消费的完整契约，`run()` 仍然是便捷路径而不是完整状态通道。
- 这次变更不会新增第三方依赖，也不会改动五个顶层公开导出名字，但会对 `AgentEvent.status` 的可取值集合形成一次公开契约升级。
