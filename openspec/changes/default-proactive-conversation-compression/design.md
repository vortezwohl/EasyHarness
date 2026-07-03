## Context

EasyHarness 目前已经有自己的 `EventingSummarizingConversationManager` 包装层，但默认构造仍然沿用上游 Strands 的隐式默认值。这导致一个不太优雅的边界问题：SDK 虽然已经对 conversation compression 负责发事件、定义公开语义，却没有真正拥有默认压缩策略本身。

这次变更的核心不是“让压缩更激进”，而是让 EasyHarness 对外提供一套清晰、稳定、可验证的默认策略：

- 默认启用 proactive compression
- 默认 `summary_ratio=0.3`
- 默认 `preserve_recent_messages=8`
- 默认策略必须写进 README
- 调用方仍可显式覆盖默认值

这里的约束也很明确：

- 不能破坏现有 `compress` 事件语义
- 不能影响 `Agent(..., conversation_manager=custom_manager)` 的透传优先级
- 不能为了几个默认值再新增一层 SDK 配置对象

## Goals / Non-Goals

**Goals:**

- 让默认 conversation compression 行为由 EasyHarness 显式定义，而不是隐式继承上游默认值。
- 把 proactive compression 的默认阈值、摘要比例和最近消息保留数变成可测试的 SDK 契约。
- 保持默认 manager 的构造可覆盖性，让高级调用方无需 fork SDK 就能调整策略。
- 在 README 中明确压缩策略，降低默认行为的惊讶成本。

**Non-Goals:**

- 不新增新的公开配置层、环境变量或 profile 机制。
- 不修改 `compress` 事件格式、状态词汇或失败控制流。
- 不改变自定义 `conversation_manager` 的透传语义。
- 不重新设计 summary 算法、消息分片策略或上游 Strands 压缩流程。

## Decisions

### 1. EasyHarness 显式拥有默认压缩策略，而不是继续透传上游隐式默认值

**Decision**

`EventingSummarizingConversationManager` 将声明自己的默认构造参数，而不是继续只接受 `*args, **kwargs` 并完全沿用上游默认值。

默认策略定义为：

- `summary_ratio=0.3`
- `preserve_recent_messages=8`
- `proactive_compression={"compression_threshold": 0.7}`

**Rationale**

这一步把“EasyHarness 默认行为”从上游实现细节提升成 SDK 契约。最关键的是 `proactive_compression`：如果只写成 `True`，SDK 仍然依赖上游当前版本把默认阈值解释为 `0.7`。把阈值显式固定为 `0.7` 更稳定，也更容易文档化和测试。

**Alternatives considered**

- 保持当前 `*args, **kwargs` 透传：最省代码，但默认策略继续不透明。
- 只把 `proactive_compression=True` 作为默认值：看起来简单，但仍然把阈值绑定到上游隐式常量。
- 新增单独的 EasyHarness 压缩配置对象：过度设计，当前需求只需要稳定默认值和覆盖能力。

### 2. 默认值只作用于 SDK 默认 manager，不扩散到自定义 manager

**Decision**

`Agent` 在未传入 `conversation_manager` 时，继续创建 `EventingSummarizingConversationManager`；一旦调用方传入自定义 manager，SDK 仍然原样透传，不再注入这组默认值。

**Rationale**

这保持了边界清晰：

- SDK 默认路径有稳定策略
- 高级调用方的自定义策略保持完全自主

这样既不会削弱 EasyHarness 的默认体验，也不会污染高级集成方的运行时策略。

**Alternatives considered**

- 把默认值注入所有 manager：侵入性太强，也违背已有透传语义。
- 提供二次包装自定义 manager 的机制：复杂度高，当前没有必要。

### 3. 显式覆盖能力通过构造参数保留，不新增额外扩展点

**Decision**

`EventingSummarizingConversationManager` 继续允许调用方通过构造参数覆盖：

- `summary_ratio`
- `preserve_recent_messages`
- `proactive_compression`
- 以及上游支持的其他参数

实现上优先使用显式签名，然后把参数原样传递给 `SummarizingConversationManager`。

**Rationale**

这比保留纯 `**kwargs` 更可读，也比增加单独 setter / builder 更简单。调用方式仍然是 Python 原生构造参数，没有新的概念负担。

**Alternatives considered**

- 维持只有 `**kwargs` 的签名：扩展灵活，但默认值和可覆盖项都不够直观。
- 新增工厂函数：多一层 API，没有收益。

### 4. README 把压缩机制作为用户可观察行为写清楚

**Decision**

README 将新增一节 conversation compression 说明，至少明确：

- 默认使用事件化 summarizing conversation manager
- 默认开启 proactive compression
- 默认 proactive threshold 为上下文窗口的 `70%`
- 默认 `summary_ratio=0.3`
- 默认 `preserve_recent_messages=8`
- `AgentEvent(kind="compress", ...)` 会暴露压缩事件
- 调用方可以通过自定义 manager 或显式参数覆盖默认策略

**Rationale**

proactive compression 是用户可观察行为，不是纯内部实现。只在代码里改默认值而不写文档，会让“为什么还没 overflow 就开始 summary”变成排障成本。

**Alternatives considered**

- 只在代码注释里记录：对 SDK 使用者不可见。
- 只在测试里体现：对维护者有帮助，但对调用方没有说明力。

## Risks / Trade-offs

- **[风险] 默认 proactive compression 让压缩更早发生，部分调用方会更快看到 `compress` 事件** → 在 README 明确阈值和触发方式，并保留显式覆盖能力。
- **[风险] `preserve_recent_messages` 从 10 改到 8 会让更旧消息更早进入 summary** → 保持 `summary_ratio=0.3` 不变，降低行为扰动面；同时为新默认值补充测试。
- **[风险] 若继续跟随上游布尔默认值，未来升级 Strands 可能静默改变阈值** → 在 SDK 内显式固定 `0.7`，把默认阈值变成 EasyHarness 自己的契约。
- **[风险] 显式签名需要随着上游新增参数做同步维护** → 保留对上游关键参数的兼容透传，必要时只做小范围跟进，不引入新的中间抽象层。

## Migration Plan

1. 调整 `EventingSummarizingConversationManager` 构造默认值，使 SDK 默认路径使用新的 proactive policy。
2. 保持 `Agent(..., conversation_manager=custom_manager)` 路径不变，确保没有自定义 manager 回归。
3. 为默认参数、proactive compression 事件和覆盖路径补充测试。
4. 在 README 新增 conversation compression 说明，记录默认阈值与覆盖方式。
5. 如果实现或验证发现默认 proactive 行为对现有测试假模型过于敏感，优先修正测试建模方式，而不是回退 SDK 默认策略。

## Open Questions

- 无阻塞问题。
- 实现阶段只需要决定 README 将压缩机制放在 `Event Stream` 前还是后；这属于文档组织问题，不影响方案本身。
