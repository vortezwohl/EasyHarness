# Design Catalog

## Metadata
- Document Type: Design Catalog
- Document ID: DESIGN-CATALOG
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Approved Design Bundle
- Design IDs: D-001, D-002, D-003
- Approval Evidence: The user confirmed every compatibility choice and manually entered architect-propose.
- Bundle Digest: Reject the empty fixed tuple syntax, enforce fail-fast single-session ownership, and make the existing Ruff gate fully pass.

## Designs
| Design ID | Path | Title | Design Digest |
| --- | --- | --- | --- |
| D-001 | 03-designs/D-001-reject-empty-fixed-tuple-context.md | Reject Empty Fixed Tuple Context | Reject tuple[()] at registration and preserve valid tuple forms. |
| D-002 | 03-designs/D-002-single-session-reentrancy-gate.md | Single Session Reentrancy Gate | Expose AgentBusyError for fail-fast single-session ownership. |
| D-003 | 03-designs/D-003-restore-ruff-quality-gate.md | Restore Ruff Quality Gate | Repair full Ruff output without changing configuration. |
