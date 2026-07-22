# Task: T-004-verify-and-document-context-contract

## Metadata
- Document Type: Task
- Document ID: T-004
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Design Sources
- Source Design References: D-001, D-002, D-003
- Design Rule References: R-D001-001, R-D001-002, R-D002-002, R-D002-003, R-D003-001, R-D003-002, R-D003-003
- Prohibited New Concepts: No dependency injection container, global Context store, plugin registry, static checker plugin, or model-visible Context surface.

## Preconditions
- T-001 through T-003 are complete and all implementation behavior is stable enough to verify.

## Functional Boundary
- Requested Functionality: Close the upgrade with full regression coverage and English documentation of the approved public contract.
- Protected Functionality: Context schema hiding, safe failure redaction, per-invocation maps, ordinary input validation, and unrelated runtime behavior remain unchanged.
- Explicit Non-Goals: Do not add dependencies, unions, positional-only support, broad typing forms, coercion, or global state.
- Compatibility Guarantees: ToolContext[T] | None retains migration behavior; inheritance remains unsupported; public exports remain available.
- Mandatory Stop Condition: Stop if the task needs Context visibility, serialization, a new dependency, or an unapproved ordinary-parameter contract change.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| tests/test_sdk.py | Context test suite | Verify all success, failure, schema, and concurrency seams. | Primary verification surface. |
| tests/旧版本教程.md | Context tutorial | Update English examples, defaults, containers, and migration guidance. | Existing tutorial path. |
| easyharness/__init__.py | Public export check | Confirm public surface remains correct. | SDK boundary. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: The listed locations own the approved Context seam.
- Scope Expansion Decision Rule: Add a direct dependency only after confirming it is necessary, minimal, and inside the functional boundary.
- Required Assessment and Record: Log evidence, alternatives, affected locations, protected-contract impact, and verification result.

## MUST DO
- M-T004-001: Document only approved Context behavior in English.
- M-T004-002: Run focused Context tests, the full SDK module, diff checks, and encoding checks.
- M-T004-003: Record actual verification outcomes and unavailable tooling.

## MUST NOT DO
- N-T004-001: Do not document unsupported typing forms or unimplemented security guarantees.
- N-T004-002: Do not claim a validation passed when it did not run.

## Atomic Steps
1. Review tests against the verification matrix.
2. Update the English tutorial.
3. Run focused and full SDK tests.
4. Run diff and encoding checks and record outcomes.

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
Documentation and tests state one contract, required verification evidence is recorded, and no Context value becomes model-visible.
