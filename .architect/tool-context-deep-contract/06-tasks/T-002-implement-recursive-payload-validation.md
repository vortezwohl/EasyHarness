# Task: T-002-implement-recursive-payload-validation

## Metadata
- Document Type: Task
- Document ID: T-002
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Design Sources
- Source Design References: D-001, D-002
- Design Rule References: R-D001-001, R-D002-001, R-D002-002, R-D002-003, R-D002-N001, R-D002-N002
- Prohibited New Concepts: No dependency injection container, global Context store, plugin registry, static checker plugin, or model-visible Context surface.

## Preconditions
- T-001 is complete and produces normalized payload specifications.

## Functional Boundary
- Requested Functionality: Implement recursive no-coercion validation for approved scalar, parent-class, and dict/list/tuple/set payloads.
- Protected Functionality: Context schema hiding, safe failure redaction, per-invocation maps, ordinary input validation, and unrelated runtime behavior remain unchanged.
- Explicit Non-Goals: Do not add dependencies, unions, positional-only support, broad typing forms, coercion, or global state.
- Compatibility Guarantees: ToolContext[T] | None retains migration behavior; inheritance remains unsupported; public exports remain available.
- Mandatory Stop Condition: Stop if the task needs Context visibility, serialization, a new dependency, or an unapproved ordinary-parameter contract change.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/tools.py | Payload validator and direct/stream type checks | Replace class-only checks with one matcher. | Current validation owner. |
| tests/test_sdk.py | Container and safe-error coverage | Add deep matching regressions. | Existing error-contract coverage. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: The listed locations own the approved Context seam.
- Scope Expansion Decision Rule: Add a direct dependency only after confirming it is necessary, minimal, and inside the functional boundary.
- Required Assessment and Record: Log evidence, alternatives, affected locations, protected-contract impact, and verification result.

## MUST DO
- M-T002-001: Deeply validate every supported container member.
- M-T002-002: Preserve subclass compatibility and redact raw payload values.
- M-T002-003: Warn when explicit None matches ToolContext[object].

## MUST NOT DO
- N-T002-001: Do not coerce, copy, serialize, cache, freeze, or mutate Context payloads.
- N-T002-002: Do not accept Any, Protocol, unions, or unsupported typing expressions.

## Atomic Steps
1. Validate the closed annotation grammar.
2. Add the recursive matcher with cycle protection.
3. Route direct and stream checks through it.
4. Add nested-container and safe-failure tests.

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
All supported payload shapes match deeply, invalid nested members fail safely, and unsupported types fail during registration.
