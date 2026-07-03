## Context

EasyHarness 当前已经把底层 Strands runtime 包装成极简公开表面，但这个包装在“停止当前运行”这一件事上还停在半路：

- 底层 `strands.Agent` 已经支持线程安全的 `cancel()`
- EasyHarness 公开 `Agent` 只暴露 `run()`、`stream()` 和 `reset()`
- 公开 `AgentEvent.status` 只有 `started`、`delta`、`completed`、`failed`

这会让上层 UI 陷入两个不优雅的分叉：

1. 控制面没有标准入口，只能绕过 SDK 触碰内部对象；
2. 事件面没有 `cancelled` 终态，只能把取消硬塞进 `completed`、`failed` 或字符串文本。

对一个把“统一事件流”作为核心卖点的 SDK 来说，这个缺口不是局部实现问题，而是公开契约不完整。与此同时，这次变更也有明确约束：

- 不能破坏 `easyharness` 只暴露五个顶层名字的公开表面原则；
- 不能把底层 Strands 的原始事件结构直接泄露给上层；
- 不能为了取消能力顺手引入新的 `Harness`、`SessionHandle` 或并行结果对象；
- 必须让上层 UI 在不推断内部线程行为的前提下，稳定判断一次 invocation 是否被取消。

## Goals / Non-Goals

**Goals:**

- 为公开 `Agent` 提供标准、幂等、线程安全的 `cancel()` 能力。
- 让 `AgentEvent` 能把取消表达为一等终态，而不是完成或失败的变体。
- 让 `agent.stream(...)` 在取消场景下输出适合 UI reducer 消费的稳定事件序列。
- 保持当前 SDK 的极简风格，不新增并行 runtime 入口或公开内部桥接对象。
- 保持取消后的 Agent 可继续复用，不要求调用方在每次取消后强制 `reset()`。

**Non-Goals:**

- 不把“停止消费 Python generator”自动升级成底层 invocation 取消。
- 不在这次变更里重新设计 `run()` 的返回类型，也不新增公开 `AgentResult`。
- 不暴露底层 Strands 的完整 `stop_reason` 枚举给上层，SDK 只公开自己需要稳定维护的语义。
- 不处理多 invocation 并发控制模型；当前仍以单个 `Agent` 同时只跑一个 invocation 为前提。

## Decisions

### 1. 公开 `Agent.cancel()`，内部只做最薄的 runtime 透传

**Decision**

在公开 `Agent` 上新增 `cancel()` 实例方法，由 `_StrandsRuntime.cancel()` 直接透传到底层 `self._agent.cancel()`。

**Rationale**

这是最小、最稳、最符合当前边界的做法：

- 取消能力已经存在于底层，不需要重造取消状态机；
- 公开层只负责把能力纳入 SDK 标准用法；
- 控制面依旧只有一个主入口 `Agent`，不引入新的 handle 或 side channel。

这也保留了未来扩展空间：如果以后要在取消时加入 tracing、hooks 或统计逻辑，仍然可以收口在 `_StrandsRuntime.cancel()`，不用改变调用方形态。

**Alternatives considered**

- 让调用方通过 `agent._runtime._agent.cancel()` 使用内部对象：破坏封装，等于承认 SDK 表面不完整。
- 新增 `AgentRunHandle` / `InvocationController`：对当前规模过度设计，会把极简 API 做胖。
- 仅为 `stream()` 返回一个可取消对象：会让 `run()` 和 `stream()` 的控制模型分裂，不适合当前 SDK。

### 2. 把“取消”建模为 `status`，而不是新增 `kind`

**Decision**

将公开 `EventStatus` 从四态扩展为五态：

- `started`
- `delta`
- `completed`
- `failed`
- `cancelled`

取消不会新增 `kind="cancel"`；相反，取消会作为现有阶段事件的终态出现，例如 `assistant.cancelled`、`thinking.cancelled`、`tool.cancelled`。

**Rationale**

`kind` 代表“事件属于哪个运行时阶段”，`status` 代表“这个阶段处于什么生命周期”。取消并不是新的阶段，它只是现有阶段的一种停止方式。把取消建模为 `status` 有三个好处：

- UI reducer 不需要认识新的阶段类型；
- 同一个时间线组件可以统一渲染 completed / failed / cancelled 三种终态；
- 未来若增加别的阶段种类，取消语义可以天然复用，而不需要为每个阶段额外发一条独立 cancel 事件。

**Alternatives considered**

- 新增 `kind="cancel"`：语义重复，UI 需要自己再反推“哪个阶段被取消”。
- 继续只用 `completed` / `failed` 并在 `data.stop_reason` 里区分：表面上 diff 小，实际上把关键语义藏进 payload，不适合作为 SDK 公开契约。

### 3. `stream()` 成为完整取消契约的权威接口，`run()` 保持便捷路径

**Decision**

取消相关的完整阶段语义只保证在 `agent.stream(prompt)` 中可见。`run(prompt)` 继续保留为同步文本便捷接口，不额外升级成结构化结果通道。

**Rationale**

这是最符合当前 SDK 形状的分层：

- `stream()` 本来就承担 runtime 可视化和 UI 消费职责；
- `run()` 的价值是最短调用路径，而不是承载完整事件状态；
- 如果为了 cancel 把 `run()` 升级成结构化公开结果对象，会把这次改动从“补齐控制与事件契约”扩大成“重设计公开返回值模型”。

这个决策也足够有远见：以后如果真的需要公开 `AgentResult`，那可以作为单独 change 推进，而不是在 cancel 需求里顺手塞进来。

**Alternatives considered**

- 让 `run()` 在取消时抛公开异常：会引入新的同步控制契约，和当前字符串返回模型割裂。
- 让 `run()` 返回 `str | AgentResult`：类型不稳定，最差。
- 现在就公开 `AgentResult`：方向未必错，但明显超出本次最小闭环。

### 4. 取消时同时发出“阶段终态”和“系统收口事件”

**Decision**

当 invocation 被取消时，事件流应当同时满足两层语义：

- 当前活跃阶段收到自己的 `cancelled` 终态；
- 额外发出 `AgentEvent(kind="system", status="cancelled", data={"stop_reason": "cancelled"})` 作为整轮 invocation 的统一收口。

如果取消发生在尚未进入 assistant 输出、thinking 或 tool 阶段之前，则至少必须发出系统收口事件。

**Rationale**

只发阶段终态不够，因为上层还需要知道“整轮已经结束”；只发系统终态也不够，因为时间线需要知道“是哪个阶段被打断”。双层语义让 UI 能同时做好两件事：

- 更新当前阶段时间线；
- 关闭输入锁、按钮状态和运行中指示器。

**Alternatives considered**

- 只发系统取消事件：时间线信息不完整。
- 只发阶段取消事件：整轮停止原因需要 UI 自己推断。

### 5. 取消原因在 SDK 内做归一化，不把底层 stop_reason 原样上抛

**Decision**

EasyHarness 只公开自己认可的取消终态和必要的 `data.stop_reason`，而不是把底层 Strands 的全部 stop reason 细节直接映射到公开状态枚举中。

**Rationale**

SDK 的职责是提供稳定契约，而不是让上层 UI 与底层框架的词汇表耦合。把取消作为 SDK 自己维护的高层语义归一化后，未来即使底层实现细节变化，EasyHarness 仍然可以守住外部兼容性。

**Alternatives considered**

- 原样透传 Strands stop reason：短期省事，长期公开契约不稳。
- 完全不暴露 stop reason：对系统收口和调试不够友好。

## Risks / Trade-offs

- **[风险] `EventStatus` 扩充为 `cancelled` 属于公开契约升级，严格穷举状态的调用方需要跟进** → 在 spec、README 和变更说明中明确这是新增终态，不把取消继续伪装成旧状态。
- **[风险] 某些取消发生在尚未出现公开阶段事件之前，UI 可能只收到 `system.cancelled`** → 在契约里明确“系统收口事件始终存在，阶段终态按实际活跃阶段出现”。
- **[风险] 调用方误以为丢弃 `stream()` 迭代器就等同于取消** → 文档中明确声明：显式停止必须调用 `agent.cancel()`。
- **[风险] 后续若要让 `run()` 也暴露结构化停止原因，当前设计会留下能力不对称** → 在设计上有意保留这条升级路径，但本次不提前引入更重的公开结果对象。

## Migration Plan

1. 为 `Agent` 和内部 runtime 增加公开 cancel 控制入口。
2. 扩展 `EventStatus`，并在 event mapper 中把底层取消结果归一化为公开 `cancelled` 终态。
3. 调整 `stream()` 取消收口逻辑，确保阶段终态和系统终态同时满足契约。
4. 为取消中的 `stream()`、取消中的 `run()`、取消后复用、无活跃阶段取消等路径补充测试。
5. 更新 README 与示例，明确 `stream()` 是 UI 级完整状态接口，`run()` 是文本便捷接口。

## Open Questions

- 当前无阻塞性开放问题。
- 实现阶段只需要决定 `system.cancelled` 是否固定携带 `data={"stop_reason": "cancelled"}` 以外的辅助字段；这属于 payload 细节，不影响整体方案。
