## Why

`EasyHarness` 当前还是一个空壳包，但目标并不是再做一个大而全 AI 平台，而是给想开发类似 Claude Code 的软件的 Python 程序员提供一个真正可用、可读、可调、可扩展的底层 agent loop SDK。现在推进这项变更是合适的，因为 `SmartIPO` 已经验证了会话型 Agent、Strands runtime bridge、严格工具合同和时间线事件流这几类核心能力，适合在复杂度还低的时候抽离成一个独立、极简、面向人类开发者的 SDK。

## What Changes

- 新增一个极简公开 SDK 表面，只暴露 `Agent`、`ModelConfig`、`AgentEvent`、`ToolOutput` 和 `tool` 五个顶层名字。
- **BREAKING** 明确 `Agent` 是唯一主 API，不引入 `Harness`、`ToolRegistry`、内部合同对象或其他并行入口。
- 新增默认会话型 agent loop，支持连续多轮会话、流式 assistant 输出、thinking/tool 自动计时，以及对上层 UI 友好的统一事件流。
- 新增简单直接的模型配置入口 `ModelConfig`，要求开发者直接传入 `model` 与 `api_key`，默认 `base_url` 为 OpenAI 官方地址，不提供环境变量约定，不引入 channel/provider profile 层。
- 新增严格的 `@tool` 装饰器合同，要求开发者完整填写 `purpose`、`when_to_use`、`parameters`、`returns`、`common_failures` 等字段，并确保函数签名、类型注解与工具文档保持一致。
- 新增公开 `ToolOutput` 作为高级工具返回结构，用于向模型与 UI 同时提供 `data`、`model_text`、`preview`、`detail` 等信息。
- 新增默认会话压缩能力：默认使用 `SummarizingConversationManager`，同时允许开发者透传自定义 `ConversationManager`，不重新设计 Strands 的记忆体系。
- 新增底层压缩事件机制，在默认摘要压缩前后复用统一事件总线发出 `compress_started`、`compress_completed`、`compress_failed`，供 TUI/WebUI 直接消费，而不必自行推断摘要行为。
- 明确本次不做 UI 组件、timeline reducer、环境变量系统、配置文件加载器、插件系统、多智能体 orchestration、业务工具大全或项目脚手架。

## Capabilities

### New Capabilities
- `agent-sdk-surface`: 定义 `easyharness` 的极简公开 SDK 表面、`Agent` 主入口、公开导出边界和会话型调用方式。
- `model-configuration`: 定义 `ModelConfig` 的直接传参方式、默认值、OpenAI 官方 `base_url` 约定以及无环境变量策略。
- `tool-definition-contract`: 定义严格的 `@tool` 合同、参数与文档对齐规则，以及 `ToolOutput` 的公开返回语义。
- `runtime-event-stream`: 定义 `easyharness` 的底层事件机制、thinking/tool/assistant 事件流、统一 `AgentEvent` 形态和自动计时语义。
- `conversation-compression`: 定义默认 `SummarizingConversationManager` 行为、自定义 conversation manager 接入方式，以及 `compress_started` / `compress_completed` / `compress_failed` 压缩事件。

### Modified Capabilities

- None.

## Impact

- 受影响目录主要位于 `easyharness/` 与 `openspec/`，重点是新增 SDK 公开层、内部运行时桥接层与相应规范文档。
- 运行时将继续建立在 `litellm`、`prompt4py`、`vortezwohl`、`strands-agents[litellm]` 和 `fileglide` 之上，但会把复杂度压在内部适配层，不向开发者公开这些内部合同。
- 公开 API、默认配置和事件机制会成为后续实现与文档的核心边界，因此本次方案会优先明确最小可用表面而不是扩张能力面。
