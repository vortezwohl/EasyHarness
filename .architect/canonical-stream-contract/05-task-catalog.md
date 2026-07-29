# Task Catalog

## Metadata
- Document Type: Task Catalog
- Document ID: TASK-CATALOG
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Tasks
| Task ID | Execution Order | Path | Depends On | Source Design References | Summary |
| --- | --- | --- | --- | --- | --- |
| T-001 | 1 | 06-tasks/T-001-public-event-contract.md | None | D-001 | 定义并验证唯一公开 AgentEvent 契约。 |
| T-002 | 2 | 06-tasks/T-002-runtime-signal-projector.md | T-001 | D-001, D-002 | 用私有 signal 与 phase 投影器实现契约。 |
| T-003 | 3 | 06-tasks/T-003-contract-verification.md | T-001, T-002 | D-001, D-002 | 补齐序列测试、文档和全局验证。 |
