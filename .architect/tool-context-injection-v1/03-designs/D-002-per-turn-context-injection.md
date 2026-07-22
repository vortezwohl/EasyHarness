# Design: D-002-per-turn-context-injection

## Metadata
- Document Type: Design
- Document ID: D-002
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Concept
- Canonical Name: Per-turn explicit Context injection via invocation state
- Category: Runtime boundary / Adapter
- Reference: Strands `invocation_state` 与 `_EasyHarnessTool.stream()`

## Intent
调用方在每次 `run()` / `stream()` 中按函数 Context 参数名显式提供值，并安全传到实际 callable。

## Stable Core and Variation
模型调用、工具选择、普通参数验证、ToolOutput、会话和事件保持稳定；每回合 Context 的值、数量与所需工具变化。调用方拥有实例，state 仅保存引用。

## Repository Evidence
`Agent.run()` / `.stream()` 当前仅接收 prompt，新增 `**tool_contexts` 是增量；`_StrandsRuntime` 是透传点；底层 Strands 每次调用支持独立 `invocation_state`；工具 stream 已获取它。

## Compatibility Boundary
旧 `run(prompt)` / `stream(prompt)` 保持。Context key 必须由 Agent 已注册工具声明；同名 key 必须同类型、同可空性，否则构造期失败。`prompt` 为保留名；未知 key 在调用开始前失败。

## Pattern Decision
- Candidate: Adapter
- Category: Structural
- Repository seam: invocation-state map 到隐藏强类型 kwargs
- Stable core: JSON schema 与用户 callable
- Real variation: 每调用宿主依赖
- Why it fits: 将底层 state 转换为命名且类型受约束的函数参数。
- Simpler direct design considered: Tool 临时字段；拒绝，并发会串回合。
- Neighbor patterns rejected: Proxy、Decorator、Facade 不解决回合参数转换。
- Misuse risk if forced: 容器/注册中心超过单一适配问题。
- Verification seam: 连续/并发、多 Context、缺失、类型、事件。

## External Evidence Decision
采用显式依赖和现有 Strands state 接口，拒绝 Singleton、线程全局与外部框架类层级复制。

## Rationale
每次调用建立私有 `_easyharness_tool_contexts` 映射，分别传给同步调用和 `stream_async`。先验证模型普通输入，再读取 state、按名称注入、校验缺失/类型/可空性，最后执行函数。未调用的工具不因缺 Context 失败；可空未提供时保留 Python 默认值。

## Alternatives
- Context 加入 schema：拒绝，模型可伪造。
- prompt 约束：拒绝，不是授权边界。
- Agent/Tool 保存 Context：拒绝，跨回合泄露。
- ContextVar：拒绝，线程与 async 隐式传播难审计。

## Functional Boundary
- 目标功能：回合级按名称注入并在执行前校验。
- 保护功能：会话、取消、事件顺序、普通工具与 Strands 调用。
- 非目标：自动构造、默认/缓存/共享 Context、隐式线程状态。
- 硬停止条件：不得在 Tool、Agent 或模块全局保存 Context。

## Code Impact Scope
`easyharness/_internal/runtime.py`、`easyharness/_internal/tools.py`、`tests/test_sdk.py`、`README.md`、`openspec/specs/runtime-event-stream/spec.md`、`openspec/specs/agent-sdk-surface/spec.md`。

## Verification Seams
同步/流式注入；连续及并发不串值；实际调用工具缺 Context 才失败；可空默认值保留；未知 key 提前失败；同名类型冲突构造期失败。

## Counterexamples
`scope: str` 是普通输入；同名 `ctx` 的 Context 类型冲突必须拒绝；未调用工具不得失败；无该 key 的 Agent 传入 Context 必须失败。

## Anti-Patterns
Tool 当前 Context 字段；事件/异常序列化 Context；必需参数静默 None；逐工具注入；容忍类型冲突。

## Rules

### MUST DO
- R-D002-001: 每次调用创建私有 Context 映射并以 invocation state 传递。
- R-D002-002: 在用户函数前校验，公开 event input 仅含普通参数。

### MUST NOT DO
- R-D002-N001: 不得放入 Pydantic 输入、会话、模型消息、tool result 或默认 debug 字段。
- R-D002-N002: 不得用 Context 值影响工具选择或改变旧工具 schema/结果。
- R-D002-001: Context is per-turn and travels only through private invocation state.
- R-D002-002: Context is resolved only for the tool actually invoked.
