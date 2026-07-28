# Task Catalog

## Metadata
- Document Type: Task Catalog
- Document ID: TASK-CATALOG
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Tasks
| Task ID | Execution Order | Path | Depends On | Source Design References | Summary |
| --- | --- | --- | --- | --- | --- |
| T-001 | 1 | 06-tasks/T-001-relax-message-adapter.md | None | D-001 | 放宽消息 Adapter，只保留核心可映射性校验。 |
| T-002 | 2 | 06-tasks/T-002-make-conversation-management-explicit.md | T-001 | D-002 | 默认关闭压缩并限定根包会话类型导出。 |
| T-003 | 3 | 06-tasks/T-003-verify-public-contracts-and-quality.md | T-001, T-002 | D-001, D-002 | 覆盖公开契约、reset、默认语义与定向质量门禁。 |