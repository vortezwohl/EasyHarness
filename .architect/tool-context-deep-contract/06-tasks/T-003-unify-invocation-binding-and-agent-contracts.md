# Task: T-003-unify-invocation-binding-and-agent-contracts

## Metadata
- Document Type: Task
- Document ID: T-003
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Design Sources
- Source Design References: D-001, D-003
- Design Rule References: R-D001-002, R-D001-003, R-D003-001, R-D003-002, R-D003-003, R-D003-N001, R-D003-N002
- Prohibited New Concepts: No dependency injection container, global Context store, plugin registry, static checker plugin, or model-visible Context surface.

## Preconditions
- T-001 and T-002 are complete; normalized specifications and matching are available.

## Functional Boundary
- Requested Functionality: Apply one Context resolution order to direct and Agent paths and merge same-name contracts by payload only.
- Protected Functionality: Context schema hiding, safe failure redaction, per-invocation maps, ordinary input validation, and unrelated runtime behavior remain unchanged.
- Explicit Non-Goals: Do not add dependencies, unions, positional-only support, broad typing forms, coercion, or global state.
- Compatibility Guarantees: ToolContext[T] | None retains migration behavior; inheritance remains unsupported; public exports remain available.
- Mandatory Stop Condition: Stop if the task needs Context visibility, serialization, a new dependency, or an unapproved ordinary-parameter contract change.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/tools.py | Direct signature, resolver, and stream call | Share binding and fallback rules. | Both invocation paths are owned here. |
| easyharness/_internal/runtime.py | Agent Context contracts | Compare normalized payloads without optionality. | Current conflict owner. |
| tests/test_sdk.py | Direct and Agent Context cases | Cover defaults, optional fallback, and mixed optionality. | Existing integration seam. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: The listed locations own the approved Context seam.
- Scope Expansion Decision Rule: Add a direct dependency only after confirming it is necessary, minimal, and inside the functional boundary.
- Required Assessment and Record: Log evidence, alternatives, affected locations, protected-contract impact, and verification result.

## MUST DO
- M-T003-001: Apply explicit value, source default, optional None, and required failure in that order.
- M-T003-002: Use one resolver for direct and Agent execution.
- M-T003-003: Retain one private Context map per Agent invocation.

## MUST NOT DO
- N-T003-001: Do not drop source defaults or expose Context in schemas or events.
- N-T003-002: Do not store Context on Agent instances or globals.

## Atomic Steps
1. Project and bind the public direct signature.
2. Centralize Context resolution.
3. Merge Agent contracts by payload only.
4. Add default, mixed-optionality, and missing-required tests.

## Functional Boundary Conflict Protocol
- Escalation Trigger: A required implementation conflicts with a protected contract, approved payload grammar, or the no-new-dependency limit.
- Required Conflict Analysis: Compare preserving the boundary with the smallest changed behavior, identify affected callers and verification consequences, and state the exact blocking evidence.
- Recommended Option: `1`
- Recommendation Rationale: Preserve the sealed functional boundary unless the user explicitly approves a revised architecture decision.
- Decision Prompt: Reply with `1` to preserve the boundary and defer the conflict, or `2` to approve a revised boundary with its stated compatibility impact.
- Decision Limit: The decision covers only this task's identified conflict and the minimum necessary scope.
- Required Decision Record: Record the selected option, evidence, affected code, resulting behavior, and verification outcome in state and log.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Preserve the approved boundary and defer the conflict. | Delivers the sealed portion only. | Protected behavior remains unchanged. | No unapproved contract change. | Focused regression tests. |
| 2 | Approve a revised boundary for the described conflict. | May expand the task. | Requires explicit impact review. | Requires documented migration effects. | New targeted and regression tests. |

## Required Verification Evidence
- Verification Procedure: Run focused tests for this task and preserve all required regression seams.
- Required Evidence: Commands, pass/fail assertions, clean diff output, and any unavailable tooling.

## Completion Criteria
Both invocation paths resolve Context identically; same-name equivalent payload tools coexist and mismatched payloads still fail.
