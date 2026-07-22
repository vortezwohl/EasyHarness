# Plan Manifest

## Metadata
- Document Type: Plan Manifest
- Document ID: PLAN
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us
- Plan Digest: ec442e533f22c5387a72a1a5208e0dbd5847554b1419e3bf964d54ef4f91b201

## Objective
Replace inheritance-based tool Context declarations with explicit annotation syntax, reject ambiguous Context unions during tool registration, and make optional Context omission resolve to `None` consistently for agent and direct decorated-tool calls.

## Non-Goals
- Do not retain a compatibility path for Context subclasses.
- Do not change normal model-input parameter validation or the Strands invocation protocol.
- Do not add a dependency-injection container, Context registry, or cross-turn Context persistence.

## Approved Design Bundle
- Design IDs: D-001, D-002
- Approval Evidence: The user approved the displayed bundle by selecting a breaking upgrade and requiring optional Context omission for direct Python calls, then manually invoked `architect-propose`.
- Bundle Digest: context-annotation-contract-and-unified-invocation-semantics

## Architect Build Entry Conditions
- The implementation must follow D-001 and D-002 without reintroducing inheritance compatibility.
- All Context declarations must normalize to one internal contract before schema creation or invocation.
- Build must stop and request a decision if a protected model-input contract or a non-approved compatibility layer becomes necessary.
