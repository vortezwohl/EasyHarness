# Task: T-001-compile-context-parameter-specifications

## Metadata
- Document Type: Task
- Document ID: T-001
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-002, R-D001-003, R-D001-N001, R-D001-N002
- Prohibited New Concepts: No dependency injection container, global Context store, plugin registry, static checker plugin, or model-visible Context surface.

## Preconditions
- D-001 is approved; current parsing and schema-exclusion behavior are understood.

## Functional Boundary
- Requested Functionality: Compile and validate one complete Context parameter specification during tool registration.
- Protected Functionality: Context schema hiding, safe failure redaction, per-invocation maps, ordinary input validation, and unrelated runtime behavior remain unchanged.
- Explicit Non-Goals: Do not add dependencies, unions, positional-only support, broad typing forms, coercion, or global state.
- Compatibility Guarantees: ToolContext[T] | None retains migration behavior; inheritance remains unsupported; public exports remain available.
- Mandatory Stop Condition: Stop if the task needs Context visibility, serialization, a new dependency, or an unapproved ordinary-parameter contract change.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/types.py | ToolContext annotations | Preserve the public metadata syntax. | Public declaration owner. |
| easyharness/_internal/tools.py | _ToolContextParameter and parser | Capture normalized payload, defaults, kind, and ordering. | Current registration owner. |
| tests/test_sdk.py | Context registration coverage | Add focused declaration tests. | Existing verification seam. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: The listed locations own the approved Context seam.
- Scope Expansion Decision Rule: Add a direct dependency only after confirming it is necessary, minimal, and inside the functional boundary.
- Required Assessment and Record: Log evidence, alternatives, affected locations, protected-contract impact, and verification result.

## MUST DO
- M-T001-001: Compile one normalized Context specification for every recognized parameter.
- M-T001-002: Reject unions, unsupported annotations, positional-only parameters, and invalid Context ordering at registration.

## MUST NOT DO
- N-T001-001: Do not restore inheritance-based declarations.
- N-T001-002: Do not add a public specification API or global registry.

## Atomic Steps
1. Inspect current registration behavior.
2. Extend the internal specification and parser.
3. Validate defaults, kind, and ordering.
4. Add focused registration tests.

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
Valid declarations compile once; invalid declarations fail at registration with safe, precise errors.
