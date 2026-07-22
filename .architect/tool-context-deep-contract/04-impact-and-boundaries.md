# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Functional Boundary
- The plan changes internal Context declaration parsing, payload validation, direct-call binding, and same-name Agent contract comparison only.
- It must stop if the target requires Context model visibility, serialization, a new dependency, payload unions, positional-only support, or a protected ordinary-tool behavior change.

## Protected Functionality
- Tool schemas, metadata, and event inputs keep Context hidden.
- Invocation Context maps remain private and per-call.
- Unknown Context names fail at Agent entry; failed Context injection does not expose raw values or execute the tool body.
- Non-Context input validation and unrelated runtime behavior remain unchanged.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/types.py | ToolContext and OptionalToolContext | Preserve annotation syntax and metadata contract. | Public Context declaration owner. |
| easyharness/_internal/tools.py | Context parsing, matching, direct binding, stream resolution | Implement D-001 through D-003. | Current behavior owner. |
| easyharness/_internal/runtime.py | _build_tool_context_contracts | Merge same-name payload contracts without optionality. | Current Agent contract owner. |
| tests/test_sdk.py | Context test block | Add contract and regression coverage. | Existing verification seam. |
| tests/旧版本教程.md | Context tutorial | Update English guidance and migration examples. | Existing Context tutorial path. |

## Impact Scope Audit Findings
- The scope covers known production, test, and tutorial owners; fixture or helper expansion requires a recorded minimal assessment.
- Build must minimize and log any additional in-boundary location.

## Functional Boundary Conflict Readiness
- Every task records protected behavior, a mandatory stop condition, and numbered decision options for a real conflict.
