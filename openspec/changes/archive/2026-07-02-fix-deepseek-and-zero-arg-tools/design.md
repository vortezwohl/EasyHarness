## Context

`EasyHarness` 当前的公开 SDK 表面已经稳定，但这次暴露的问题都落在内部运行时边界上，而不是公开 API 设计上。

- `easyharness._internal.tools.tool()` 当前把 `parameters` 视为必须为非空映射，导致零参数函数无法声明成工具。
- `easyharness._internal.model.build_runtime_model()` 当前一律返回 `LiteLLMModel`。当模型走 DeepSeek V4 的 OpenAI 兼容接口时，底层会复用 `strands.models.openai.OpenAIModel` 的消息格式化逻辑；该逻辑在多轮里会对 `reasoningContent` 打 warning 并过滤，这与 DeepSeek V4 在 thinking + tool-call 场景下的要求不一致。
- 用户已经明确本次不处理示例脚本的相对路径问题，因此设计必须把修改面限定在 SDK 核心运行时与其测试上。

这次变更横跨工具合同和模型适配两个内部模块，虽然改动不大，但都属于核心边界行为，适合先用设计文档锁定方案，避免实现时扩散成新的 provider 抽象层。

## Goals / Non-Goals

**Goals:**

- 允许零参数函数在严格 `@tool` 合同下合法声明为工具。
- 保持现有工具合同的严格性，不放松非零参数函数的元数据对齐规则。
- 为 DeepSeek V4 的多轮 thinking/tool-call 场景提供最小定向兼容路径。
- 避免 DeepSeek 路径继续落入 OpenAI 兼容消息格式化时对 `reasoningContent` 的错误过滤。
- 为上述两类行为补充最小回归验证，确保后续重构不会回退。

**Non-Goals:**

- 不修改示例脚本的相对路径行为。
- 不新增公开 API 名字、环境变量约定或 provider 配置层。
- 不引入通用 provider registry、strategy factory 或新的模型抽象层。
- 不尝试一次性覆盖所有 OpenAI-compatible provider 的 `reasoningContent` 差异。

## Decisions

### 1. 仅放开“零参数函数 + 空参数映射”这一种合同例外

**Decision**

调整 `tool()` 的元数据校验规则：

- 当函数签名没有参数时，允许 `parameters={}`。
- 当函数签名包含参数时，`parameters` 仍必须完整且与签名完全一致。

**Rationale**

当前限制并没有提升工具合同质量，只是平白阻止 `ping()`、`cwd()`、`now()` 这类天然零参数工具。把例外收敛到“空签名 + 空映射”这一种情况，可以修复真实缺口，同时继续保留严格合同。

**Alternatives considered**

- 完全放松 `parameters` 非空校验：会削弱合同约束，不必要。
- 保持现状，让调用方通过虚假参数绕过：会污染工具定义，本质是让用户为 SDK 缺陷买单。

### 2. DeepSeek 兼容通过极薄子类覆盖消息格式化，而不是重做模型体系

**Decision**

在 `easyharness._internal.model` 中保留现有 `LiteLLMModel` 作为默认路径；仅当配置被识别为 DeepSeek V4 兼容路径时，返回一个极薄的 EasyHarness 私有子类，由它覆盖消息格式化相关入口。

该子类只解决一件事：避免多轮 tool-call 场景错误复用 OpenAI Chat Completions 的 `reasoningContent` 过滤逻辑。

**Rationale**

问题的根因不在 `Agent` 或事件层，而在底层 provider 兼容格式化分支。直接在模型构建处做最小分流，修改面最小，也最符合当前 SDK “把复杂度压在内部适配层”的边界。

**Alternatives considered**

- 一刀切对 DeepSeek 丢弃全部 `reasoningContent`：能消除 warning，但会丢掉真正需要的上下文，不是根因修复。
- 新建 provider registry / strategy：抽象明显过度，当前只有一个特例，不值得。
- 直接 fork 整个 `LiteLLMModel`：风险过大，后续跟随上游升级成本高。

### 3. DeepSeek 识别同时考虑模型名和 base_url

**Decision**

DeepSeek 兼容分支的命中条件同时考虑：

- `model` 是否显式带有 `deepseek` 特征；
- `base_url` 是否指向 DeepSeek 官方兼容接口。

命中任一稳定特征即可进入 DeepSeek 定向路径，但判断逻辑保持私有，不暴露给 SDK 用户配置。

**Rationale**

只看模型名会漏掉兼容别名；只看 `base_url` 又可能误伤通过代理接入的其他模型。双信号判断可以在不引入配置层的前提下降低误判。

**Alternatives considered**

- 只看模型名：过脆。
- 只看 `base_url`：过宽。
- 新增公开 `provider` 字段：违背现有直接传参设计。

### 4. 只在需要的多轮 tool-call 场景保留 reasoning 上下文

**Decision**

DeepSeek 子类不做“所有多轮都保留 reasoningContent”的粗暴处理，而是只在 assistant 上一轮含 tool call 且后续请求需要维持 thinking/tool-call 连贯性时保留必要的 reasoning 内容。

非该场景保持最小消息集，不把 DeepSeek 兼容逻辑扩展成新的通用消息保留规则。

**Rationale**

方案 B 的价值就在于“定向修正根因，不扩大行为面”。无脑保留全部 reasoning 会把兼容补丁变成新的隐式策略，后续难以维护。

**Alternatives considered**

- 全量保留 reasoning：实现省事，但风险外溢。
- 完全不保留 reasoning：继续保留现有 bug。

### 5. 回归验证聚焦两条最小闭环

**Decision**

这次只补两组最小测试：

- 零参数工具：验证空签名允许、非空签名仍拒绝空 `parameters`。
- DeepSeek 消息格式化：验证包含 `reasoningContent -> toolUse -> toolResult` 的历史在 DeepSeek 路径下不会错误过滤关键 reasoning 内容。

**Rationale**

这是典型的边界修复，不需要引入大而全的 provider 测试矩阵。留下能卡住回归的最小测试，比扩张测试框架更合适。

## Risks / Trade-offs

- **[风险] DeepSeek 识别条件误判** → 通过模型名与 `base_url` 双信号降低误判，并把逻辑收敛在私有构建函数中，便于后续微调。
- **[风险] 只覆盖消息格式化入口仍可能遗漏上游特殊路径** → 先为当前真实失败路径补测试；若后续发现还有旁路，再按失败点补最小覆盖，而不是预建抽象。
- **[风险] 保留 reasoning 的条件判断过宽或过窄** → 用“上一轮 assistant 含 tool call”的最小条件起步，并通过历史消息测试固定行为。
- **[风险] 上游 `strands` / `litellm` 升级导致子类覆盖点变化** → 让覆盖面尽量小，只覆写格式化相关入口，减少跟随成本。

## Migration Plan

1. 调整工具合同校验，允许零参数函数配空参数映射。
2. 在模型构建处加入 DeepSeek 私有分流，并实现极薄兼容子类。
3. 为零参数工具与 DeepSeek 历史消息格式化补最小回归测试。
4. 运行现有 SDK 回归测试与新增测试，确认默认路径未回退。
5. 如实现失败，可先回滚 DeepSeek 子类分流，不影响工具合同修复；两项改动可以独立撤回。

## Open Questions

- 当前无阻塞性开放问题。实现阶段只需要根据本设计选定最小覆写入口，不需要再引入新的范围讨论。
