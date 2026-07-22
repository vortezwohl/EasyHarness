# Task: T-002-unify-context-call-binding

## Metadata
- Document Type: Task
- Document ID: T-002
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Design Sources
- Source Design References: D-002
- Design Rule References: R-D002-001, R-D002-002, R-D002-003, R-D002-004, R-D002-N001, R-D002-N002, R-D002-N003, R-D002-N004

## Preconditions
- T-001 completed with one normalized Context contract representation.
- Required and optional Context declarations are already excluded from schemas.
- Existing runtime Context privacy behavior remains covered by focused tests.

## Functional Boundary
- Requested Functionality: Use normalized contracts to inject omitted optional Context as `None` for runtime and direct decorated-tool calls, while preserving required Context enforcement.
- Protected Functionality: Unknown-name failures, per-turn Context state, error redaction, and normal parameter behavior remain unchanged.
- Explicit Non-Goals: Context factories, cross-turn caching, normal input runtime type validation, and changes to the Strands protocol.
- Compatibility Guarantees: The new direct-call behavior intentionally treats optional Context omission as a default `None`.
- Mandatory Stop Condition: Stop if a shared implementation requires user-function code mutation, separate direct and runtime rules, or a change to the Strands call protocol.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/tools.py` | Context resolver, direct `__call__`, signature exposure | Bind arguments using normalized contracts, inject optional `None`, validate explicit Context values, and expose accurate signature semantics. | Current direct calls bypass resolver behavior. |
| `easyharness/_internal/runtime.py` | Invocation contract aggregation and per-turn map | Feed normalized names into invocation state and preserve unknown-name validation. | Runtime manages host-provided Context names. |
| `tests/test_sdk.py` | Runtime and direct-call tests | Add tests for optional omission, required failures, wrong types, direct calls, and signature reflection. | D-002 requires all paths to agree. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: These locations own decorated-tool binding, runtime invocation state, and focused SDK behavior tests.
- Scope Expansion Decision Rule: Add a helper or documentation path only if it is necessary to reflect direct-call semantics and remains within D-002.
- Required Assessment and Record: Record the requirement, affected path, rejected alternatives, and verification in the execution log and state.

## MUST DO
- M-T002-001: Reuse the normalized Context contract for runtime resolution and decorated-tool direct calls.
- M-T002-002: Inject `None` when an optional Context parameter is omitted from either supported invocation path.
- M-T002-003: Preserve required Context, unknown-name, and redacted failure behavior.
- M-T002-004: Make decorated-tool signature introspection match optional Context default semantics.

## MUST NOT DO
- N-T002-001: Do not preserve a bare direct-call passthrough for optional Context parameters.
- N-T002-002: Do not mutate user function code objects or construct implicit domain Context values.
- N-T002-003: Do not retain Context values after one agent invocation.
- N-T002-004: Do not introduce broad runtime validation for normal parameters.

## Atomic Steps
1. Refactor Context resolution into shared binding helpers that accept the normalized contract list.
2. Update runtime injection so a missing optional Context name resolves to `None` without relying on the original function default.
3. Update decorated-tool direct calls to bind arguments, add omitted optional Context values, validate supplied Context values, and invoke the original function.
4. Publish an introspection signature that displays optional Context parameters with a `None` default.

## Functional Boundary Conflict Protocol
- Escalation Trigger: A shared binding implementation would require changing the Strands protocol, retaining different direct and runtime rules, or modifying user function code objects.
- Required Conflict Analysis: Identify the divergent path, compare a compliant shared helper with the requested incompatible change, and show impacts on required Context failures, privacy, and signature behavior.
- Recommended Option: `1`
- Recommendation Rationale: The sealed design requires one Context contract and rejects protocol or user-function mutation.
- Decision Prompt: Reply with `1` to stop and preserve the shared-contract boundary, or `2` to approve the specifically described boundary change.
- Decision Limit: This decision covers only the discovered invocation conflict and its minimum necessary implementation scope.
- Required Decision Record: Record the selected option, runtime evidence, affected paths, behavior change, and verification result in state and log.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Stop and preserve one shared Context binding contract. | The conflicting portion remains unimplemented. | Protects direct/runtime consistency and user-function ownership. | No unapproved invocation behavior is introduced. | Confirm no conflicting code change was applied. |
| 2 | Approve the described boundary change. | Enables the incompatible implementation path. | May change protected invocation or privacy behavior. | Requires explicit user approval of the resulting behavior. | Verify the approved new behavior and all affected Context paths. |

## Required Verification Evidence
- Verification Procedure: Run focused runtime and direct-call tests, then inspect decorated-tool signature behavior.
- Required Evidence: Omitted optional Context resolves to `None` in both paths; required failures and Context privacy remain intact.

## Completion Criteria
Runtime and direct decorated-tool calls apply the same optional Context semantics, and signature reflection exposes the actual direct-call contract.
