## Context

EasyHarness 当前的默认运行时已经拥有 proactive conversation compression，因此上下文窗口大小不再只是底层 provider 的内部细节，而是会直接影响 SDK 的公开运行时行为。现在的问题不在于“能不能继续跑”，而在于 SDK 没有把这项元数据责任收口干净：

- `ModelConfig` 没有公开 `context_window_limit`
- `LiteLLMModel` 路径没有自动解析上下文窗口元数据
- 默认 conversation manager 会启用 proactive compression
- 底层只能在运行时回退到通用默认值 `200000` 并打印 warning

如果简单把 `ModelConfig.context_window_limit` 的默认值直接写成 `200000`，确实能让 warning 消失，但那只是把底层的猜测前移到了公开 API。这样会把“兜底值”伪装成“可信默认值”，责任边界反而更模糊。

因此，这次设计的目标不是单纯静音，而是建立一条清晰、稳定、可覆盖的解析链：

- 调用方知道真实窗口时可以显式指定
- SDK 对已知模型尽量给出准确值
- 只有在确实未知时才使用统一兜底值

## Goals / Non-Goals

**Goals:**

- 为 `ModelConfig` 增加公开、直接、可选的 `context_window_limit` 覆盖能力。
- 让 EasyHarness 在构建 runtime model 时稳定解析上下文窗口大小，而不是依赖下游 warning fallback。
- 统一处理带 provider 前缀的模型 ID，避免已知模型因为命名格式差异而丢失元数据解析能力。
- 对未知模型保持稳定兜底行为，使 proactive compression 仍然可用且不再噪音告警。

**Non-Goals:**

- 不引入新的 provider metadata registry、profile system 或外部配置文件。
- 不试图为每个 provider 维护完整的独立模型数据库；优先复用上游 Strands 已有 lookup 能力。
- 不在这次变更中重新设计 conversation compression 策略、阈值或事件格式。
- 不把 `context_window_limit=200000` 宣布为公开配置层的“真实默认模型能力”。

## Decisions

### 1. `ModelConfig` 新增可选 `context_window_limit`，但公开默认值保持 `None`

**Decision**

在公开 `ModelConfig` 中新增：

- `context_window_limit: int | None = None`

`None` 表示“调用方未显式声明”，而不是“模型窗口就是 200000”。

**Rationale**

这让公开 API 保持诚实：

- 调用方知道真实窗口时，可以显式覆盖；
- 调用方不知道时，不需要被迫理解 provider 细节；
- SDK 仍然可以在内部继续解析和兜底。

如果把公开默认值直接设成 `200000`，调用方会自然把它理解为 EasyHarness 对模型能力的正式声明，而这实际上只是兜底估算值。

**Alternatives considered**

- 公开默认值直接设为 `200000`：最省事，但语义不诚实。
- 不新增字段，只做内部自动解析：对高级调用方不够可控。

### 2. 运行时采用三段式解析顺序：显式值 > 已知模型解析 > 最终兜底

**Decision**

在 `build_runtime_model()` 路径中引入统一解析逻辑，顺序固定为：

1. `ModelConfig.context_window_limit` 显式值
2. 已知模型查表解析
3. 未知模型兜底 `200000`

解析完成后，EasyHarness 直接把 resolved `context_window_limit` 写入底层 `LiteLLMModel` 配置。

**Rationale**

这条链路同时满足四个目标：

- 调用方 override 优先级最高
- 已知模型尽量准确
- 未知模型稳定可用
- 底层不会再自己打印“未设置，使用默认值”的 warning

**Alternatives considered**

- 只做显式值和兜底值两段式：会浪费已知模型元数据能力。
- 继续依赖下游 fallback：行为可运行，但责任边界不完整。

### 3. 复用 Strands 的 lookup 能力，但在 EasyHarness 内补 provider 前缀归一化

**Decision**

EasyHarness 应优先复用 Strands 现有的 context-window lookup 表，但在调用查表前补一层轻量归一化，至少处理：

- 原始模型 ID
- 去掉 provider 前缀后的模型 ID，例如 `openai/gpt-4.1-mini` -> `gpt-4.1-mini`

**Rationale**

当前上游 lookup 对 `gpt-4.1-mini` 可解析，但对 `openai/gpt-4.1-mini` 不可解析。既然 EasyHarness 公开层允许使用 provider-prefixed model ID，就应当在本层把这类格式差异收掉，而不是要求调用方自己猜上游 lookup 的偏好。

**Alternatives considered**

- 复制一份完整 lookup 表到 EasyHarness：维护成本不必要地升高。
- 完全不做前缀归一化：会让大量本来已知的模型错误落入兜底值。

### 4. 兜底值保留为内部 runtime 默认，而不是公开语义承诺

**Decision**

对无法解析的模型，EasyHarness 仍然使用 `200000` 作为最终 runtime fallback，但这个值只属于内部解析策略，不作为 `ModelConfig` 的公开字段默认值对外承诺。

**Rationale**

这是最简单也最负责任的平衡：

- 行为稳定，不会因为未知模型缺元数据就失去 proactive compression
- 公开语义诚实，不把兜底值假装成真实模型窗口
- 后续若要替换成更好的未知模型策略，也不会破坏公开配置层契约

**Alternatives considered**

- 未知模型不兜底、直接禁用 proactive compression：准确但体验退化更明显。
- 对所有未知模型都要求调用方显式传值：对默认使用路径过于苛刻。

## Risks / Trade-offs

- **[风险] `200000` 仍然可能低于或高于某些未知模型的真实窗口** → 明确它是 runtime fallback，并允许调用方显式覆盖。
- **[风险] provider 前缀归一化规则过于保守，仍可能漏掉个别代理格式** → 先覆盖最常见的 `<provider>/<model>` 形式，后续按真实案例增量扩展。
- **[风险] 新增公开字段后，调用方可能误以为必须手动填写** → 在文档里明确该字段是可选覆盖项，普通路径不必强制提供。

## Migration Plan

1. 为 `ModelConfig` 增加可选 `context_window_limit` 字段，并更新文档说明。
2. 在 runtime model 构建处引入上下文窗口解析 helper。
3. 将 resolved 值显式传入 `LiteLLMModel` 路径。
4. 为显式 override、已知模型解析、provider 前缀归一化和未知模型 fallback 补充测试。

## Open Questions

- 当前无阻塞性开放问题。
- 实现阶段只需要决定“provider 前缀归一化”是否先只支持单个 `/` 分隔格式；这属于 helper 细节，不影响整体方案。
