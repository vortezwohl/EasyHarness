# Design Catalog

## Metadata
- Document Type: Design Catalog
- Document ID: DESIGN-CATALOG
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Approved Design Bundle
- Design IDs: D-001, D-002
- Approval Evidence: 用户选择破坏性重构后，以 `.w` 调用 `architect-propose`，覆盖最新展示的完整设计包。
- Bundle Digest: 用无歧义公开事件信封和私有强类型 signal 投影器，移除文本全量终态与旧协议兼容。

## Designs
| Design ID | Path | Canonical Concept | Design Digest |
| --- | --- | --- | --- |
| D-001 | 03-designs/D-001-canonical-stream-contract.md | Append-only phase event contract | 文本仅经 delta，终态不含文本，事件有顺序和 phase 身份。 |
| D-002 | 03-designs/D-002-typed-signal-projector.md | Adapter plus explicit finite phase lifecycle | 上游事件转私有 signal，再按 phase 生命周期投影。 |
