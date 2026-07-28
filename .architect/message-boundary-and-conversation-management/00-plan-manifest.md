# Plan Manifest

## Metadata
- Document Type: Plan Manifest
- Document ID: PLAN
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN
- Plan Digest: 2097ea09422859fb3a7a0d4516e93839fcffc09c10b401b0ef7be07b8cfd6f1c

## Objective
落实已批准的消息边界与显式会话管理：消息适配器只拒绝无法映射的典型错误；默认不压缩；根包仅导出两个指定会话管理器。

## Non-Goals
- 不接受或拼接输入消息中的 system、developer。
- 不支持未实现真实映射的多模态内容、Responses API、会话替换或历史工具重放。
- 不修改无关的 ToolContext 失败、全仓既有格式问题或其他公开 API。

## Approved Design Bundle
- D-001-openai-message-boundary：用户在展示设计包后的下一回合显式调用 architect-propose，构成批准证据。
- D-002-explicit-conversation-management：同一回合批准；允许默认压缩语义发生破坏性变更。
- 核心决策：单一 Adapter 放宽可映射消息；显式 NullConversationManager 取代默认摘要；根包只增加指定导出。

## Architect Build Entry Conditions
- 仅执行 T-001、T-002、T-003，按目录顺序进行。
- 每项任务须保留受保护功能并完成声明验证，再推进下一项。
- 若实现要求接受 system/developer、静默丢弃不可映射内容、恢复默认压缩或扩大导出面，必须停止并执行任务冲突协议。
