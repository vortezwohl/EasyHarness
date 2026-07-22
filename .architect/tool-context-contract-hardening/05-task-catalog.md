# Task Catalog

## Metadata
- Document Type: Task Catalog
- Document ID: TASK-CATALOG
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Tasks
| Task ID | Execution Order | Path | Depends On | Source Design References | Summary |
| --- | --- | --- | --- | --- | --- |
| T-001 | 1 | 06-tasks/T-001-reject-empty-tuple-context.md | None | D-001 | Reject the unsupported empty fixed tuple Context annotation. |
| T-002 | 2 | 06-tasks/T-002-add-agent-reentrancy-gate.md | T-001 | D-002 | Add the fail-fast Agent busy gate and public exception. |
| T-003 | 3 | 06-tasks/T-003-restore-ruff-gate.md | T-001, T-002 | D-003 | Restore the full Ruff quality gate without relaxations. |
