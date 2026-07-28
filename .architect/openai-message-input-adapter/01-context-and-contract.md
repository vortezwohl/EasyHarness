# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

## Observed Facts
- `easyharness/_internal/runtime.py` 的公共与私有 `run` / `stream` 目前声明 `prompt: str` 并直接传给 Strands。
- Strands 1.45.0 的 `Messages` 仅接受 `user`、`assistant` role，且每条消息的 `content` 是内容块列表。
- Strands 以 assistant `toolUse` 与 user `toolResult` 表达工具历史；EasyHarness 的模型层已能把它们格式化为 OpenAI `tool_calls` 与 `tool` 消息。
- 现有 SDK 测试覆盖会话复用、取消、Context 注入和 DeepSeek 工具历史，但没有公共 OpenAI 输入适配覆盖。

## Approved Input Limits
- 公开入参类型为 `str | list[dict]`。
- 列表仅接受 OpenAI Chat Completions 的 user、assistant、tool 文本/function-call 子集。
- `system`、`developer` 和任何不支持的 role、字段或结构均抛出 `ValueError`，不得静默丢弃。

## Compatibility Intent
- 保持 `run("...")`、`stream("...")` 行为完全兼容；列表输入是增量能力。
- 规范化后的列表消息追加到现有 Agent 会话历史；不会替换历史。
- 仅构造 Agent 时提供的 `system_prompt` 可影响系统提示。

## Functional Boundary
- Requested Functionality: 在 EasyHarness 内部将字符串和允许的 OpenAI 消息列表统一转换为 Strands `Messages`，供 run 和 stream 共用。
- Protected Functionality: 字符串兼容性、会话追加、系统提示所有权、Context 注入、取消、压缩、事件、懒惰 stream、单会话互斥。
- Explicit Non-Goals: 多模态、Responses API、会话替换、历史工具自动执行、provider 专有 reasoning 和工具名注册校验。
- Compatibility Guarantees: 不变更既有字符串调用的返回、事件或生命周期；列表输入只追加规范化消息。
- Mandatory Stop Condition: 若需要让列表覆盖或补充 `system_prompt`、静默忽略 `system` / `developer`，或改变追加历史语义，必须停止。

## Preserved Contracts
- `Agent.run(prompt, **tool_contexts)` 与 `Agent.stream(prompt, **tool_contexts)` 的 Context 参数及错误处理。
- `_StrandsRuntime` 的调用占用和释放时机，以及 stream 首次消费时才开始执行的语义。
- Strands 作为唯一的会话历史、压缩和模型循环所有者。

## Explicitly Permitted Contract Changes
- 将两个公开方法及对应私有方法的 `prompt` 类型扩展为 `str | list[dict]`。
- 新增可观察的 `ValueError`，用于拒绝先前不被该 API 接受的列表输入中不支持的结构。

## Execution Constraints
- 保持最小 diff，优先在 `runtime.py` 中实现一个无状态私有适配函数，禁止创建未被设计要求的新架构层。
- 所有新增或修改的 Python 文档字符串、注释和公开说明使用中文，文件编码为 UTF-8 without BOM。
- 完成每个任务后执行其声明的局部验证，再执行完整验证矩阵。
