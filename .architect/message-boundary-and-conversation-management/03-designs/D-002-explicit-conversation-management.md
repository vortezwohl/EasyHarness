# Subdesign: D-002-explicit-conversation-management

## Metadata
- Document Type: Design
- Document ID: D-002
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Concept
- Canonical Name: Explicit Dependency Composition
- Category: Direct design
- Reference: Strands NullConversationManager、SlidingWindowConversationManager、SummarizingConversationManager。

## Intent
未传 conversation_manager 的 Agent 完整保留历史且不自动压缩；压缩或裁剪只能由调用方明确传入 manager 选择。

## Stable Core and Variation
稳定的是 Agent 生命周期、reset 和显式 manager 注入；变化的是调用方选择无管理、滑动窗口或摘要策略。

## Repository Evidence
- clone_conversation_manager(None) 当前创建 EventingSummarizingConversationManager，默认 0.7 主动摘要。
- Strands manager 为 None 时默认 SlidingWindowConversationManager。
- NullConversationManager 不改写历史，真实溢出时重新抛出异常。
- runtime.py reset 从原始 manager 模板创建新的 Strands Agent。

## Compatibility Boundary
用户明确允许默认压缩行为变化。显式 manager、reset、事件绑定和不可 deepcopy manager 的既有回退必须保留。

## Pattern Decision
不选择 GoF 模式。只有一个透明默认值，Strands 已提供策略对象；Factory/Strategy 外包装会隐藏默认语义，Decorator/Proxy/Facade 也没有对应职责。

## External Evidence Decision
Strands 本地实现是默认语义的直接事实。GoF 比较仅用于排除没有真实变化点的抽象。

## Rationale
显式构造 NullConversationManager 是绕过 Strands None 默认滑动窗口的唯一方式。默认超大消息完整交给模型，超限时传播错误，符合默认不压缩。

## Alternatives
继续默认 Eventing 摘要违反边界；传 None 给 Strands 仍得 SlidingWindow；新增 manager factory 会扩大 API 并隐藏选择。

## Functional Boundary
- conversation_manager=None 得到新的 NullConversationManager。
- 根包只新增 EventingSummarizingConversationManager 和 SlidingWindowConversationManager。
- 显式任意 ConversationManager 保持克隆与 event sink 行为。
- reset 为默认和可 deepcopy 官方 manager 重建干净会话。
- 不承诺不可 deepcopy 自定义 manager 的完整重置。

## Code Impact Scope
- easyharness/_internal/conversation.py 的默认构造与英文文案。
- easyharness/_internal/runtime.py 的默认 manager 描述。
- easyharness/__init__.py 的受限导出。
- tests/test_sdk.py 与 README.md 的装配、默认语义与 reset 说明。

## Verification Seams
- 默认类型为 NullConversationManager，超大消息无压缩事件或历史改写。
- 显式 Eventing manager 仍可发出压缩事件。
- 显式 Sliding manager 可从根包导入并管理历史。
- reset 后默认或官方 deepcopy manager 不带旧会话历史。

## Counterexamples
reset 不会清空调用方外部消息列表。不可 deepcopy 自定义 manager 可能复用状态，不能承诺完整记忆隔离。

## Anti-Patterns
- 将 None 透传给 Strands 并误称关闭管理。
- 继续默认摘要或窗口压缩。
- 导出 ConversationManager、NullConversationManager、原始 SummarizingConversationManager 或其他类型。
- 用隐藏 factory 或全局配置选择 manager。

## Rules

### MUST DO
- R-D002-001: conversation_manager=None 时显式创建新的 NullConversationManager。
- R-D002-002: 根包仅导出指定 EventingSummarizingConversationManager 与 SlidingWindowConversationManager。
- R-D002-003: 保留显式 manager 的 deepcopy 优先、原对象回退和 event sink 逻辑。
- R-D002-004: 以英文代码文案和最小用户文档说明默认不压缩与显式 manager。

### MUST NOT DO
- R-D002-N001: 默认路径不得摘要、裁剪或发射 compress event。
- R-D002-N002: 不得扩大根包会话类型公开面。
- R-D002-N003: 不得修改 reset 并发保护、会话追加或未批准的 manager 生命周期。
