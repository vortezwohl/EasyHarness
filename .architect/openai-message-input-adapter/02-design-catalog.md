# Design Catalog

## Metadata
- Document Type: Design Catalog
- Document ID: DESIGN-CATALOG
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

## Approved Design Bundle
- Design IDs: D-001
- Approval Evidence: 用户先确认系统角色拒绝、列表追加和字符串兼容；随后发送 `.w [$architect-propose]`，依 `architect-design` 审批规则批准最新 D-001。
- Bundle Digest: 一个严格的 OpenAI Chat Completions 输入到 Strands `Messages` 的 Adapter；系统提示保持构造期所有权。

## Designs
| Design ID | Path | Canonical Concept | Design Digest |
| --- | --- | --- | --- |
| D-001 | 03-designs/D-001-openai-message-input-adapter.md | Adapter | 统一规范化字符串与允许的 OpenAI 文本/function-tool 历史，拒绝系统角色和不支持结构。 |
