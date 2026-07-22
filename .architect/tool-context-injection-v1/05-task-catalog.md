# Task Catalog

## Metadata
- Document Type: Task Catalog
- Document ID: TASK-CATALOG
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Tasks
| Task ID | Execution Order | Path | Source Designs | Task Digest | Status |
| --- | --- | --- | --- | --- | --- |
| T-001 | 1 | 06-tasks/T-001-add-tool-context-contract.md | D-001 | Define marker and schema/metadata parameter split. | pending |
| T-002 | 2 | 06-tasks/T-002-thread-per-turn-context-through-runtime.md | D-002 | Transport a fresh Context map per call. | pending |
| T-003 | 3 | 06-tasks/T-003-enforce-context-injection-and-visibility.md | D-002, D-003 | Inject, validate, hide, and fail safely. | pending |
| T-004 | 4 | 06-tasks/T-004-document-and-verify-context-contract.md | D-001, D-002, D-003 | Document and verify the complete contract. | pending |

## Execution Order Rationale
T-001 establishes Context specifications; T-002 provides per-turn transport; T-003 applies it at the tool seam; T-004 records and verifies the public contract.