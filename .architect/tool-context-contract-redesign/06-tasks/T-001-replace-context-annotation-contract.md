# Task: T-001-replace-context-annotation-contract

## Metadata
- Document Type: Task
- Document ID: T-001
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-002, R-D001-003, R-D001-004, R-D001-N001, R-D001-N002, R-D001-N003, R-D001-N004

## Preconditions
- The sealed package remains the authority for Context behavior.
- Existing Context subclass tests are identified before they are changed.
- The implementation does not begin a legacy compatibility adapter.

## Functional Boundary
- Requested Functionality: Replace subclass-based Context declarations with `ToolContext[T]` and `OptionalToolContext[T]`, then reject invalid Context unions during tool registration.
- Protected Functionality: Context remains absent from schemas and metadata parameter matching; ordinary non-Context input unions remain unchanged.
- Explicit Non-Goals: Direct-call default injection, runtime invocation changes, legacy subclass support, and changes to ordinary input validation.
- Compatibility Guarantees: The old inheritance contract intentionally breaks and the new public wrappers are exported clearly.
- Mandatory Stop Condition: Stop if annotation parsing cannot be introduced without retaining a legacy subclass recognition path or changing normal model-input union behavior.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/types.py` | Context annotation API | Define annotation-only required and optional Context wrappers plus internal marker metadata. | D-001 replaces the current base-class marker. |
| `easyharness/_internal/tools.py` | Context declaration parser and input model | Preserve annotation metadata, normalize valid contracts, and reject invalid Context unions. | Current parser and schema filter are here. |
| `easyharness/__init__.py` | Public exports | Export the approved public annotation surface. | Public SDK import path must expose the new API. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: These files own the public type declaration, tool registration parser, schema exclusion, and public import surface.
- Scope Expansion Decision Rule: Add a directly affected documentation or test fixture path only after confirming it is necessary for the new public contract and does not introduce compatibility behavior.
- Required Assessment and Record: Record the added path, why it is directly affected, alternatives considered, and verification outcome in the execution log and state.

## MUST DO
- M-T001-001: Define `ToolContext[T]` and `OptionalToolContext[T]` as annotation syntax rather than inheritance requirements.
- M-T001-002: Normalize accepted declarations into one Context contract with a single runtime-checkable payload type and optional flag.
- M-T001-003: Reject invalid Context unions during `@tool` registration with an actionable error.
- M-T001-004: Keep normalized Context parameters out of tool schemas and metadata parameter matching.

## MUST NOT DO
- N-T001-001: Do not retain a Context subclass compatibility path.
- N-T001-002: Do not accept a Context union with multiple concrete payload alternatives.
- N-T001-003: Do not change ordinary non-Context union processing.
- N-T001-004: Do not expose Context descriptions or values to the model.

## Atomic Steps
1. Replace the old public marker definition with annotation-only required and optional wrappers while preserving runtime metadata for parser use.
2. Update tool type-hint extraction to retain annotation metadata and normalize only approved Context forms.
3. Add registration-time failure paths for invalid Context unions and runtime-uncheckable payload declarations.
4. Update schema construction and package exports for the new normalized contract.

## Functional Boundary Conflict Protocol
- Escalation Trigger: The replacement requires a subclass compatibility adapter, affects ordinary non-Context union validation, or makes Context visible to model input.
- Required Conflict Analysis: Compare the requested annotation-only design with the proposed incompatible change, identify affected public callers and code paths, and show whether a smaller compliant parser change exists.
- Recommended Option: `1`
- Recommendation Rationale: The approved breaking boundary rejects legacy compatibility and protects normal model-input behavior.
- Decision Prompt: Reply with `1` to stop and preserve the sealed boundary, or `2` to approve the specifically described boundary change.
- Decision Limit: This decision covers only the discovered conflict and its minimum necessary code surface.
- Required Decision Record: Record the selected option, conflict evidence, affected paths, compatibility result, and verification evidence in state and log.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Stop and preserve the sealed annotation-only boundary. | The conflicting portion remains unimplemented. | Protects model-input and no-legacy rules. | No unapproved compatibility behavior is added. | Confirm no conflicting code change was applied. |
| 2 | Approve the described boundary change. | Enables the identified implementation path. | May change a protected rule. | Requires explicit user-approved compatibility consequences. | Verify the approved new behavior and all affected protected paths. |

## Required Verification Evidence
- Verification Procedure: Run focused registration and schema tests after introducing the new annotation parser.
- Required Evidence: Valid required and optional Context declarations register; invalid Context unions fail during registration; Context remains hidden from schema and metadata.

## Completion Criteria
The new public annotation contract is exported, normalized at registration, rejects prohibited Context unions, and preserves Context privacy without a legacy subclass path.
