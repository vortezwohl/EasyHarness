## Context

`EasyHarness` 的目标不是成为一个大而全的 agent 平台，而是成为一个面向 Python 程序员、极简、直观、好调试的 agent loop SDK。当前仓库基本为空，但 `SmartIPO` 已经验证了几类关键能力：会话型 `Agent`、Strands runtime bridge、统一事件机制、严格工具合同，以及围绕上下文压缩和工具执行的可观测性。

这次设计需要在“足够优雅”和“不过度设计”之间取平衡。用户已经明确要求：

- 主 API 必须叫 `Agent`，而不是 `Harness`
- SDK 对外要极简，只暴露必要名字
- 默认底层使用 `SummarizingConversationManager`
- 允许透传自定义 `ConversationManager` 和 Strands 记忆能力
- 模型配置必须简单直接，默认 `base_url` 为 OpenAI 官方地址
- 不依赖环境变量，不内建 channel/profile 体系
- 工具定义必须完整、严格、可读，且不要求使用 Strands 的工具装饰器
- 底层必须提供可被 UI 消费的 timeline / thinking / tool / compress 事件，但 UI 本身不属于 SDK 责任

本次方案的关键不是“增加更多能力”，而是通过明确的边界控制，把已有 runtime 能力抽离成一个可长期维护的 SDK 表面。

## Goals / Non-Goals

**Goals:**

- 提供一个会话型 `Agent` 主入口，支持多轮连续对话、工具调用和事件流输出。
- 提供极简公开 API：`Agent`、`ModelConfig`、`AgentEvent`、`ToolOutput`、`tool`。
- 提供直接传参的模型配置方式，要求开发者显式传入 `model` 与 `api_key`，并提供清晰的默认值。
- 提供严格的 `@tool` 合同，让工具签名、类型注解、文档字段和输入 schema 保持一致。
- 提供统一的底层事件机制，让 thinking、tool、assistant、compress 都复用同一套事件管道。
- 默认使用带事件能力的 `SummarizingConversationManager`，并保留自定义 conversation manager 的接入空间。
- 把复杂度压在内部适配层，不向 SDK 用户公开 registry、bridge、validator 等内部对象。

**Non-Goals:**

- 不实现 TUI、WebUI、timeline reducer、动画或滚动管理。
- 不实现环境变量加载器、配置文件加载器、channel/profile 配置层。
- 不实现多智能体 orchestration、插件系统、项目脚手架或业务工具集合。
- 不重新设计 Strands 的 memory / conversation 子系统。
- 不把 `fileglide` 默认工具集打包进 core SDK；如需提供，后续走 `contrib` 路线。

## Decisions

### 1. 公开表面固定为五个顶层名字

**Decision**

`easyharness` 顶层只公开：

- `Agent`
- `ModelConfig`
- `AgentEvent`
- `ToolOutput`
- `tool`

所有内部合同、注册表、桥接层、校验器、provider 适配器和事件汇聚器都保留在私有模块中。

**Rationale**

用户的核心诉求是“对人类开发者直观、API 极简、封装好”。如果把 `ToolSpec`、`ToolRegistry`、runtime bridge 等内部结构一起暴露，对 SDK 用户只有理解成本，没有直接价值。`Facade` 是这里最合适的模式。

**Alternatives considered**

- 暴露 registry / spec 对象：更灵活，但会立刻扩大表面积并泄露内部结构。
- 提供 `Harness` 和 `Agent` 双入口：会把语义做重，违背“唯一主 API”目标。

### 2. `Agent` 采用会话型、同步优先的最小 API

**Decision**

`Agent` 公开最小构造参数：

- `model: ModelConfig`
- `system_prompt: str`
- `tools: list`
- `conversation_manager: object | None = None`

公开最小方法：

- `run(prompt: str) -> str`
- `stream(prompt: str) -> Iterator[AgentEvent]`
- `reset() -> None`

`run()` 与 `stream()` 都基于同一会话状态执行，而不是 one-shot 调用。

**Rationale**

Claude Code 类产品的真实使用路径是单会话内连续规划、连续调用工具、连续产生事件。会话型 `Agent` 比单轮 loop 更符合实际，同时保持 API 足够小。同步优先能降低调试门槛，避免 v1 先把复杂度花在并发表面上。

**Alternatives considered**

- stateless one-shot API：更简单，但不适合作为 Claude Code 类应用的底层。
- 同时公开 sync / async 双表面：能力更全，但会让 v1 学习成本和测试成本翻倍。

### 3. `ModelConfig` 直接传参，不做环境变量和 profile 层

**Decision**

`ModelConfig` 公开字段固定为：

- `model: str`
- `api_key: str`
- `base_url: str = "https://api.openai.com/v1"`
- `temperature: float = 0.01`
- `top_p: float = 0.01`
- `seed: int | None = None`

SDK 不读取环境变量，不提供 channel、provider profile、env name、配置文件路径等间接配置层。

**Rationale**

直接传参最符合“design for human, not for machines”。开发者用户最容易理解的模型配置就是“模型名、API Key、Base URL、采样参数”。默认 `base_url` 指向 OpenAI 官方地址，而兼容端点由调用方自行覆盖。

**Alternatives considered**

- 继承 `SmartIPO` 的 channel/profile/env 结构：更“配置驱动”，但对 SDK 用户来说是无谓认知负担。
- 读取环境变量：方便 demo，但会把调用方的部署约定耦合进底层 SDK。

### 4. 工具定义使用自有 `@tool` 装饰器，强制完整元数据

**Decision**

SDK 提供自有 `@tool` 装饰器，而不是让调用方直接使用 Strands 的工具定义方式。装饰器要求调用方完整填写：

- `name`
- `purpose`
- `when_to_use`
- `parameters`
- `returns`
- `common_failures`

并要求：

- 函数参数必须有类型注解
- `parameters` 必须覆盖全部函数参数
- 文档字段必须与函数签名对齐
- 返回值可以是 `str`、可序列化结构或 `ToolOutput`
- SDK 不强制 English-only 合同文本

**Rationale**

目标是给开发者一个清晰、严格、具有指引性的工具定义入口，同时避免让用户手写一整套冗长内部合同对象。通过装饰器 + 函数签名推导 schema，可以在保持严格的同时减少机械样板代码。

**Alternatives considered**

- 直接暴露内部 `ToolSpec`：太底层，不够 human-first。
- 放松元数据校验：看起来更灵活，但会削弱工具对模型与 UI 的可理解性。

### 5. `ToolOutput` 公开，但只保留最小语义字段

**Decision**

`ToolOutput` 公开给 SDK 用户，字段收敛为：

- `data`
- `model_text`
- `preview`
- `detail`

普通工具可直接返回 `str` 或可序列化数据；只有需要模型文本与 UI 预览分离时，才显式返回 `ToolOutput`。

**Rationale**

用户已经明确要求 `ToolOutput` 可以公开。相比隐藏在工厂方法或 registry 里，直接公开一个极小结构更直观，也能满足 timeline / tool result 预览场景。

**Alternatives considered**

- 完全不公开 `ToolOutput`：会让高级工具场景缺少清晰出口。
- 暴露更复杂的结果合同：会增加学习成本。

### 6. 统一底层事件机制，公开事件对象保持简单

**Decision**

SDK 内部继续使用统一事件总线，但公开层输出统一的 `AgentEvent`，至少承载以下语义：

- `kind`: `thinking` / `tool` / `assistant` / `compress` / `system`
- `status`: `started` / `delta` / `completed` / `failed`
- `text`
- `name`
- `started_at`
- `duration_ms`
- `data`

thinking、tool、assistant、compress 都复用同一事件机制。UI 只消费事件，不参与事件推断。

**Rationale**

UI 关心的是“发生了什么”，不该自己猜测“是不是在 thinking / tool / compress”。公开层提供统一事件对象，可以同时满足 CLI/TUI/WebUI，而不把它们绑定到某个 reducer 或 UI 框架。

**Alternatives considered**

- 公开 `channel + event_type + payload` 原始结构：更贴近内部，但对 SDK 用户不够友好。
- UI 自己推断行为：实现最省，但会带来重复逻辑和错误推断。

### 7. 默认 conversation manager 带摘要压缩事件

**Decision**

SDK 默认使用一个内部的事件化 `SummarizingConversationManager` 子类。该子类在上下文压缩开始、完成、失败时复用底层事件机制发出：

- `compress_started`
- `compress_completed`
- `compress_failed`

对应的公开 `AgentEvent` 语义为：

- `kind="compress", status="started"`
- `kind="compress", status="completed"`
- `kind="compress", status="failed"`

失败控制流保留 Strands 原始语义：

- reactive overflow recovery 失败时继续抛异常
- proactive compression 失败时记录失败事件并允许流程继续

**Rationale**

上下文压缩是 Claude Code 类应用的真实运行态行为，UI 需要知道它发生了、耗时多少、是成功还是失败。把这组事件做在 conversation manager 子类和统一 event sink 之间，能在不引入 UI 依赖的前提下提供稳定可观测性。

**Alternatives considered**

- 让 UI 根据消息长度变化推断摘要：不可靠，也会重复逻辑。
- 重新设计自有 memory 系统：不必要，违背“复用 Strands 能力”的方向。

### 8. 自定义 conversation manager 透传优先，事件接入走可选钩子

**Decision**

如果开发者传入自定义 `conversation_manager`，SDK 直接透传，不包第二层 conversation 抽象。若该对象支持 SDK 约定的可选 event sink 绑定钩子，则注入统一 sink；不支持则仅保留其原始行为。

**Rationale**

这能同时满足两个目标：

- 不重设计 Strands conversation API
- 给需要压缩事件或其他会话事件的高级调用方保留扩展点

**Alternatives considered**

- 强制自定义 manager 继承 SDK 基类：侵入性太强。
- 完全不提供事件接入：会让自定义 manager 无法复用统一事件机制。

## Risks / Trade-offs

- **[风险] 事件表面过小，后续扩展字段时可能引发兼容性顾虑** → 通过在 `AgentEvent.data` 中承载可扩展细节，保持顶层字段稳定。
- **[风险] 默认同步 API 可能限制高并发场景** → v1 明确同步优先；若后续确有需求，再在不破坏现有表面的前提下补充 async 入口。
- **[风险] 严格 `@tool` 合同提高首次接入成本** → 用签名推导 schema 减少样板，同时在文档与错误信息里明确缺失项。
- **[风险] 默认压缩事件可能暴露过多内部行为** → 事件只暴露可消费摘要、计时和状态，不默认泄露完整压缩正文。
- **[风险] `fileglide` 不进入 core 可能让本地 coding agent demo 需要额外组装** → 保持 core 干净，后续按 `contrib` 方式提供现成工具包。

## Migration Plan

1. 在 `EasyHarness` 仓库内新增 OpenSpec 方案并冻结 v1 公开边界。
2. 先实现公开 facade 和私有 runtime 适配层，再补工具合同与默认 conversation manager。
3. 在实现阶段优先建立最小运行闭环：`Agent.run()`、`Agent.stream()`、`@tool`、`ModelConfig`、事件输出。
4. 再补压缩事件、自定义 conversation manager 接入和文档示例。
5. 由于当前仓库几乎为空，本次没有存量迁移负担，也不需要回滚旧 API；若实现阶段发现公开表面过大，应优先删减而不是补抽象。

## Open Questions

- 无阻塞性开放问题。本方案已经明确 v1 的公开表面、默认值、边界和压缩事件机制，后续实现可直接按本设计推进。
