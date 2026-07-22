# Task: T-003-verify-context-contracts

## Metadata
- Document Type: Task
- Document ID: T-003
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Design Sources
- Source Design References: D-001, D-002
- Design Rule References: R-D001-003, R-D001-004, R-D002-002, R-D002-003, R-D002-004

## Preconditions
- T-001 and T-002 completed.
- Focused tests can instantiate tools and invoke both agent and direct-call paths without external provider credentials.
- The package's protected boundary remains unchanged.

## Functional Boundary
- Requested Functionality: Prove the new annotation contract, invalid-union failures, schema privacy, optional omission behavior, and required failure behavior.
- Protected Functionality: Normal input schema behavior, unknown-name failures, redacted error data, and per-turn Context lifecycle remain protected.
- Explicit Non-Goals: Broad integration testing against external models, performance redesign, or tests unrelated to tool Context contracts.
- Compatibility Guarantees: Tests codify the deliberate failure of legacy subclass declarations and the deliberate optional direct-call behavior.
- Mandatory Stop Condition: Stop if focused verification reveals a protected-contract regression that cannot be corrected within D-001 and D-002.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `tests/test_sdk.py` | Context contract coverage | Add and update focused tests for registration, schemas, runtime, direct calls, signatures, errors, and lifecycle. | This is the existing SDK contract test surface. |
| `README.md` | Public examples | Update Context examples only if existing examples use the broken inheritance API. | Breaking public syntax needs accurate documentation. |
| `tests/??.md` | Local teaching example | Update Context examples only if they document the old API. | Existing tutorial discusses Context behavior. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: Focused tests and affected public examples provide sufficient proof and migration clarity.
- Scope Expansion Decision Rule: Add only a directly related fixture or example when the existing test surface cannot express an approved verification seam.
- Required Assessment and Record: Record each added scope item, its direct connection to D-001 or D-002, and the corresponding verification evidence.

## MUST DO
- M-T003-001: Add focused tests for valid required and optional annotation declarations and invalid Context union registration failures.
- M-T003-002: Verify Context schema and metadata privacy for the new declaration forms.
- M-T003-003: Verify omitted optional Context becomes `None` in runtime and direct decorated-tool calls.
- M-T003-004: Verify required failures, unknown names, wrong types, redaction, and per-turn lifecycle remain protected.

## MUST NOT DO
- N-T003-001: Do not weaken protected assertions to accommodate a legacy inheritance path.
- N-T003-002: Do not use external model credentials as the primary verification mechanism.
- N-T003-003: Do not add unrelated SDK regression coverage under this task.
- N-T003-004: Do not document optional Context as depending on a manually declared function default.

## Atomic Steps
1. Replace old Context subclass fixtures with plain payload types used through the new annotation wrappers.
2. Add registration tests for prohibited unions and unsupported legacy declarations.
3. Add runtime and direct-call tests for omitted optional Context, required Context failures, wrong types, unknown names, and redaction.
4. Add signature and per-turn lifecycle assertions, then update affected examples.
5. Run focused tests, formatter or lint checks if configured, and the relevant broader SDK test target.

## Functional Boundary Conflict Protocol
- Escalation Trigger: Verification exposes a protected regression that cannot be fixed without changing D-001, D-002, or a protected ordinary input contract.
- Required Conflict Analysis: Identify the failing scenario, expected and actual contracts, causal implementation seam, smallest possible correction, and any design-boundary conflict.
- Recommended Option: `1`
- Recommendation Rationale: The design is sealed; an unresolved protected regression must not be hidden by broader test changes.
- Decision Prompt: Reply with `1` to stop and preserve the sealed verification boundary, or `2` to approve the specifically described boundary change.
- Decision Limit: This decision covers only the failing verification seam and its minimum necessary implementation scope.
- Required Decision Record: Record the selected option, failing evidence, affected tests and paths, compatibility consequence, and final verification result in state and log.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Stop and preserve the sealed contract. | The unresolved implementation remains incomplete. | Protects verified model-input and Context privacy rules. | No unapproved regression is accepted. | Record the failing focused test and untouched protected behavior. |
| 2 | Approve the described boundary change. | Enables the proposed regression resolution. | May change protected test expectations or behavior. | Requires explicit user approval of the new contract. | Verify the approved contract and every affected regression path. |

## Required Verification Evidence
- Verification Procedure: Run the focused Context test group, inspect the generated schema and direct-call signature, then run the relevant broader SDK test target.
- Required Evidence: Every approved declaration and invocation seam passes; every prohibited declaration fails at registration; no Context value leaks into schemas or errors.

## Completion Criteria
Tests and affected examples accurately encode the new breaking Context contract and demonstrate the protected behavior remains intact.
