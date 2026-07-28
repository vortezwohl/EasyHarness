# Design Catalog

## Metadata
- Document Type: Design Catalog
- Document ID: DESIGN-CATALOG
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Approved Design Bundle
- Design IDs: D-001, D-002
- Approval Evidence: 用户在完整设计包展示后的首个后续回合显式调用 architect-propose；覆盖 D-001 与 D-002。
- Bundle Digest: Adapter 放宽可映射消息；显式 NullConversationManager 取代默认摘要；两个用户指定 manager 是唯一新增根包导出。

## Designs
| Design ID | Path | Canonical Concept | Design Digest |
| --- | --- | --- | --- |
| D-001 | 03-designs/D-001-openai-message-boundary.md | Adapter | 将 OpenAI/provider 消息转换为 Strands Messages，只拒绝不可映射核心结构。 |
| D-002 | 03-designs/D-002-explicit-conversation-management.md | Explicit Dependency Composition | 默认使用 NullConversationManager，压缩仅由调用方显式选择。 |