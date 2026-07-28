# Subdesign: D-001-openai-message-boundary

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Concept
- Canonical Name: Adapter
- Category: Structural
- Reference: GoF Adapter；Strands Messages、Message 与 ContentBlock 官方类型。

## Intent
将 OpenAI 风格历史消息转换为 Strands 官方消息格式，只拦截无法表达或会破坏 SDK 语义的输入。

## Stable Core and Variation
稳定的是 Strands user/assistant 角色与内容块契约；变化的是调用方 metadata、文本分段、工具调用和 reasoning 文本。

## Repository Evidence
- runtime.py 的 _normalize_prompt 是唯一外部消息到 Strands Messages 的转换点。
- Strands Message 只接受 user/assistant；工具调用和结果分别是 toolUse/toolResult。
- model.py 已有 DeepSeek reasoningContent 到 reasoning_content 路径。
- 当前 unknown-field 白名单拒绝 name、文本 parts 和 provider 字段，超过必要映射范围。

## Compatibility Boundary
放宽历史消息输入，但 system/developer 继续拒绝，且不得覆盖构造期 system_prompt。字符串输入与会话追加保持不变。

## Pattern Decision
选择 Adapter，因为唯一真实问题是外部与内部消息形状不兼容。拒绝 Decorator、Proxy、Bridge、Factory、Strategy 与其余 GoF 模式：不存在职责叠加、访问策略、双变化轴、创建复杂性或算法族。

## External Evidence Decision
采用 GoF Adapter 的边界翻译原则；以 Strands 本地源代码为运行时契约。DOI 10.1016/j.infsof.2015.05.006 仅支持审慎选择模式，不替代仓库事实。

## Rationale
可确定映射的 metadata 不应阻止调用；含语义但无法表达的内容不能静默丢弃。转换创建新 Messages，避免改变调用方外部历史。

## Alternatives
直接透传外部字典违反 Strands 契约；忽略不可映射内容会丢失语义；跨消息工具配对验证会错误绑定调用方历史责任。

## Functional Boundary
- 接受 str，及由 mapping 构成的 user、assistant、tool 消息列表。
- 接受字符串和文本 content parts，保留可映射 assistant reasoning_content、tool call、tool result。
- 忽略可选 metadata/provider 字段，但不承诺其成为 Strands 运行时语义。
- 拒绝 system、developer、未知或非字符串 role、不可映射非文本内容和缺失工具核心字段。
- 不验证跨消息工具顺序、对应关系或历史完整性。

## Code Impact Scope
- easyharness/_internal/runtime.py 的 PromptInput、_normalize_prompt、run 和 stream。
- tests/test_sdk.py 的转换、失败、输入不变性和流式对称测试。
- model.py 仅在已有 reasoning 路径确有最小接入需要时进入范围。

## Verification Seams
- 调用 Strands 的对象是新建官方 Messages。
- metadata/text parts 可转换；媒体不被静默忽略。
- system/developer 与工具核心错误在模型调用前失败。
- 失败后 Agent 可复用，run 与 stream 一致。

## Counterexamples
图像、音频、文档在没有真实映射前不能伪装为文本支持；无法安全映射的 reasoning 签名不能声称无损兼容。

## Anti-Patterns
- 禁止一切未知字段的白名单。
- 静默丢弃不可映射语义。
- 在 run/stream 复制转换逻辑。
- 在 SDK 中重建外部历史工具顺序验证器。

## Rules

### MUST DO
- R-D001-001: 在一个无状态私有 Adapter 中转换并返回新建 Messages。
- R-D001-002: 只校验角色、可映射内容和工具调用的最小核心字段；忽略可选 metadata。
- R-D001-003: 对不可映射内容与工具核心错误给出包含消息索引和字段路径的英文 ValueError。
- R-D001-004: 让 run 和 stream 保持相同转换与失败契约。

### MUST NOT DO
- R-D001-N001: 不得接受、拼接或静默忽略 system、developer。
- R-D001-N002: 不得静默降级多模态或其他不可表达内容。
- R-D001-N003: 不得引入自定义 Message、策略选择器或跨消息历史语义校验。
