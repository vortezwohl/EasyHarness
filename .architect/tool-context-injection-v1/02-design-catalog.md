# Design Catalog

## Metadata
- Document Type: Design Catalog
- Document ID: DESIGN-CATALOG
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Approved Design Bundle
- Design IDs: D-001, D-002, D-003
- Approval Evidence: User-provided approved D-001 to D-003 bundle and explicit architect-propose invocation on 2026-07-22.
- Bundle Digest: Annotation-driven hidden Context, private per-turn invocation state, and non-leaking observability.

## Designs
| Design ID | Path | Canonical Concept | Design Digest |
| --- | --- | --- | --- |
| D-001 | 03-designs/D-001-tool-context-contract.md | ToolContext contract | Classify hidden Context separately from model input. |
| D-002 | 03-designs/D-002-per-turn-context-injection.md | Per-turn injection | Carry a fresh private Context mapping through runtime. |
| D-003 | 03-designs/D-003-context-visibility-and-failure-contract.md | Visibility contract | Keep public inputs and safe failures Context-free. |