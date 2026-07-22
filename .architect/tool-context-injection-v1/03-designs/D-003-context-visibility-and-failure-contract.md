# Design: D-003-context-visibility-and-failure-contract

## Metadata
- Document Type: Design
- Document ID: D-003
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Concept
- Canonical Name: Hidden Context observability and failure contract
- Category: Security-sensitive runtime contract
- Reference: 统一工具事件与 `ToolOutput`

## Intent
定义 Context 的默认不可见性和失败语义，防止从 schema、事件、metadata 或错误重新泄露。

## Stable Core and Variation
事件继续公开 tool use id、普通 input、output 和成功/失败；ToolOutput 不变。Context 是私有依赖，SDK 只保护注入路径，不能阻止工具主动输出敏感字段。

## Repository Evidence
工具事件公开 `arguments` 为 input；runtime 将 input/output 放入 `AgentEvent.data`；失败 ToolOutput 将错误文本放入可见字段，故注入错误必须安全格式化。

## Compatibility Boundary
普通事件形状不变，不新增 context 字段，不改用户显式 ToolOutput；缺失 Context 是标准工具失败，不以未处理异常中断 stream。

## Pattern Decision
- Candidate: Direct visibility boundary
- Category: Runtime contract
- Repository seam: 调用 kwargs 与公开 event input 分离
- Stable core: 用户函数调用和既有事件
- Real variation: 无
- Why it fits: 分离载荷和集中格式化足够。
- Simpler direct design considered: 注入前 arguments 原样做 public input。
- Neighbor patterns rejected: Proxy、Decorator、Observer 只增加包装而不能保证边界。
- Misuse risk if forced: 安全代理会制造假安全感。
- Verification seam: schema、event input、失败文本、隔离。

## External Evidence Decision
接受最小暴露的结构边界，拒绝靠 prompt/README 或深度脱敏任意 ToolOutput。

## Rationale
保留 `public_input = arguments`，另建 `call_kwargs = {**arguments, **resolved_contexts}`。注入错误仅包含工具名、参数名、预期类型名，绝不出现 Context repr、字段、token 或资源信息。

## Alternatives
- 深度脱敏全部 ToolOutput：拒绝，无法可靠识别领域敏感字段。
- event private Context：拒绝，消费者不一定遵守。
- README 警告：拒绝，不能替代结构防护。

## Functional Boundary
- 目标功能：Context 默认只从 invocation state 到用户函数。
- 保护功能：AgentEvent、ToolOutput、错误流和调试。
- 非目标：审计工具主动输出或净化用户异常秘密。
- 硬停止条件：不得在 schema、模型消息或公开事件新增 Context 数据。

## Code Impact Scope
`easyharness/_internal/tools.py`、`easyharness/_internal/runtime.py`、`tests/test_sdk.py`、`README.md`、`openspec/specs/runtime-event-stream/spec.md`。

## Verification Seams
schema/描述不含名；event input 不含名和值；缺失/类型错误不含 repr/字段；成功 output 只来自工具；直接调用无需 runtime。

## Counterexamples
工具显式返回 Context 字段时 SDK 不篡改；用户异常含秘密不属于本变更。

## Anti-Patterns
错误日志写完整 Context；更新 arguments 后发布；LLM `get_context()`；marker 被当作权限/脱敏系统。

## Rules

### MUST DO
- R-D003-001: 注入错误只含名称和类型名，并分离模型 arguments 与 call kwargs。
- R-D003-002: 为缺失、错误类型、事件不可见性增加测试。

### MUST NOT DO
- R-D003-N001: 不得在默认事件或错误写 Context/repr。
- R-D003-N002: 不得当作模型输入、记忆或 conversation state，也不得改写用户 ToolOutput。
- R-D003-001: Public event input contains only model-supplied ordinary arguments.
- R-D003-002: Injection failures contain names and expected type only.
