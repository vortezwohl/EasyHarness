# Subdesign: D-001-openai-message-input-adapter

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

## Concept
- Canonical Name: Adapter
- Category: GoF Structural
- Reference: GoF Adapter；`architect-design` 本地决策协议和完整 GoF 模式目录。

## Intent
在 EasyHarness 公开 API 边界把 `str | list[dict]` 严格转换为 Strands `Messages`，再进入底层 Strands Agent；传入列表绝不拥有系统提示。

## Stable Core and Variation
- 稳定核心：run、stream、持久会话、工具 Context、压缩、取消和事件映射。
- 变化：调用方可提供 OpenAI Chat Completions 的文本与 function-tool 历史；内部消息模型仍固定为 Strands `Messages`。

## Repository Evidence
- `easyharness/_internal/runtime.py` 的 `_StrandsRuntime.run`、`_StrandsRuntime.stream` 及公共 `Agent` 方法是唯一输入入口。
- Strands `Messages` 只含 `user`、`assistant`；工具历史使用 `toolUse` / `toolResult` 内容块。
- `easyharness/_internal/model.py` 已证明 Strands 与 OpenAI 工具历史之间的目标映射形状。
- `tests/test_sdk.py` 的 FakeModel、会话与工具历史测试可扩展为无网络回归覆盖。

## Compatibility Boundary
- 字符串 run/stream 完全兼容；列表为新增能力且追加到现有历史。
- 列表中的 `system` / `developer` 必须抛出 `ValueError`；构造期 `system_prompt` 不可覆盖或补充。
- 仅支持 user、assistant、tool 的文本/function-call 子集；不支持结构必须失败而非降级。

## Pattern Decision
选择 Adapter：外部 OpenAI 消息形状与内部 Strands 消息形状不兼容，转换责任应集中在一个边界。拒绝 Facade，因为没有多子系统编排；拒绝 Strategy，因为没有多个运行时转换算法；拒绝 Proxy，因为这里不改变访问控制语义。

## External Evidence Decision
接受仓库与本地架构资料作为事实和模式依据。尝试读取 ACM Parnas 论文、Google API Design Guide 与 OpenAI 官方 function-calling 页面，但当前环境分别返回 403 或超时；未读取其正文，未将其作为设计事实依据。

## Rationale
在 `runtime.py` 定义单一、无状态、无副作用的私有规范化函数，返回新建 `Messages`。`str` 变为一条 `user/text` 消息；assistant 文本和 `tool_calls` 合并为 assistant 的 text / `toolUse` 内容块；OpenAI `tool` 消息转为带 `toolResult` 内容块的 Strands user 消息。`function.arguments` 必须解析为 JSON object，tool result 统一标记 `success`。run 与 stream 在调用 Strands 前共用该函数。

## Alternatives
- 直接传递列表给 Strands：拒绝，OpenAI 的字符串 content、`tool_calls` 与 `tool_call_id` 不符合 Strands 输入契约。
- 静默过滤系统角色或未知字段：拒绝，会制造未生效却不可见的上下文丢失。
- 在 run 与 stream 分别实现转换：拒绝，会导致校验与错误语义漂移。

## Functional Boundary
- Target functionality: run/stream 接受并规范化字符串或允许的列表输入。
- Protected related functionality: 会话追加、系统提示所有权、工具 Context、事件、取消、压缩和并发占用。
- Explicit non-goals: 多模态、Responses API、会话替换、历史工具执行和 provider 专有字段。
- Hard stop: 任何需要覆盖系统提示、静默丢弃系统角色或改变会话追加的实现必须停止并请求用户决策。

## Code Impact Scope
- `easyharness/_internal/runtime.py`：输入类型、规范化函数、公共/私有 run 与 stream 签名及 docstring。
- `tests/test_sdk.py`：转换、失败、历史追加、输入不变与 run/stream 对称测试。
- `README.md`：公开输入契约与 OpenAI 历史示例。

## Verification Seams
- mock Strands 调用前的实参必须为标准 `Messages`。
- 转换后的 toolUse/toolResult ID、名称、JSON 参数和文本必须可断言。
- 系统角色和非法参数在模型调用、历史追加和工具执行前失败，失败后 Agent 可复用。
- 初始化系统提示独立保留；列表仅追加到既有历史。

## Counterexamples
- 需要图片或 Responses API 事件的调用方不适用，应另立设计。
- 需要整段列表替换内存会话的调用方不适用，应设计显式会话替换 API。
- 需要无损 provider reasoning 历史的调用方不适用，应先定义其跨模型兼容契约。

## Anti-Patterns
- 用默认空字符串、空对象或 `dict()` 强制转换掩盖非法输入。
- 忽略未知 role / 字段并继续模型调用。
- 让调用方 OpenAI 格式穿透到 Strands，或复制转换逻辑。
- 将历史 tool call 当作本轮需要自动执行的请求。

## Rules

### MUST DO
- R-D001-001: 对 `str` 和 `list[dict]` 走同一私有规范化入口，并在调用 Strands 前完成。
- R-D001-002: 返回新建消息对象，不修改调用方提供的嵌套列表或字典。
- R-D001-003: 错误必须包含消息索引与字段路径，但不得回显完整 payload。
- R-D001-004: 为 run 与 stream 建立相同的成功和失败契约测试。

### MUST NOT DO
- R-D001-N001: 不得接受或拼接列表内的 `system` / `developer`。
- R-D001-N002: 不得扩展到多模态、Responses API、会话替换或工具自动执行。
- R-D001-N003: 不得改变字符串 API 的生命周期和事件语义。
