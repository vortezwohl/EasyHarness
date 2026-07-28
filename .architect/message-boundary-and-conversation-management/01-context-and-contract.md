# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Observed Facts
- Agent.run 和 Agent.stream 经 runtime.py 的 _normalize_prompt 进入 Strands。
- 当前适配器拒绝 name、provider 扩展字段、文本 content parts 和 reasoning_content，超过实际映射所需校验。
- Strands Messages 是官方 list[Message]，角色仅为 user/assistant。
- clone_conversation_manager(None) 当前默认 EventingSummarizingConversationManager，并在 0.7 阈值主动摘要。
- Strands 在 manager 为 None 时默认 SlidingWindowConversationManager；EasyHarness 必须显式传入 NullConversationManager 才能关闭默认管理。
- reset 重建 Strands Agent 并从 manager 模板重新克隆；不可 deepcopy 的自定义 manager 复用既有回退语义。
- 完整 SDK 测试当前有一个既有 ToolContext 深层类型失败，本计划不得顺手修复。

## Approved Input Limits
- 用户允许默认会话管理发生破坏性变更。
- system 与 developer 继续拒绝。
- 根包只新增 EventingSummarizingConversationManager 和 SlidingWindowConversationManager。
- 新增或修改的代码字符串、注释与 docstring 使用英文并遵守 PEP 8。

## Compatibility Intent
保持字符串输入、构造期 system_prompt、会话追加、工具 Context、取消、事件、互斥占用和显式 manager。默认 manager 从主动摘要改为无管理是用户明确允许的变化。

## Functional Boundary
- Requested Functionality: 放宽可映射消息字段；默认不压缩；公开两个指定 manager；以 reset 支持受控重建。
- Protected Functionality: system_prompt 所有权、Strands 格式、会话追加、事件、并发与显式 manager。
- Explicit Non-Goals: system/developer、多模态静默降级、完整 provider 协议、会话替换、历史工具执行、额外导出。
- Compatibility Guarantees: 仅默认压缩语义可以改变；其他受保护行为维持。
- Mandatory Stop Condition: 不能表达输入而又需要改变受保护功能或批准范围时停止并请求用户决定。

## Preserved Contracts
- run 与 stream 都在模型调用前转换输入。
- 输入历史追加到当前会话；reset 后才开始新会话。
- system_prompt 仅在构造期拥有。
- 显式 manager 保持 deepcopy 优先、原对象回退及 event sink 绑定。

## Explicitly Permitted Contract Changes
- 未传 manager 时不再主动摘要或裁剪。
- 默认超大输入完整传给模型，真实溢出可向调用方传播。
- 可映射附加字段不再因未知字段白名单失败。

## Execution Constraints
- 直到用户手动调用 architect-build 前，只修改本计划的 .architect 文档。
- build 必须使用英文代码文案、UTF-8 无 BOM。
- 禁止全仓格式化、翻译或修复无关 lint/test 问题。