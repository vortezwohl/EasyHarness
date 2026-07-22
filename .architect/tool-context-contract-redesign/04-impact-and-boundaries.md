# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Functional Boundary
- Requested Functionality: Redesign public Context annotations, reject invalid Context unions during tool registration, and unify optional Context behavior across runtime and direct calls.
- Protected Functionality: Model-input schemas, metadata matching for ordinary parameters, Context privacy, per-turn Context lifecycle, unknown-name failures, and required Context failures.
- Explicit Non-Goals: Legacy inheritance support, normal model-input union changes, DI containers, automatic Context construction, plugin mechanisms, and broad tool-system refactoring.
- Compatibility Guarantees: The old Context inheritance contract intentionally breaks; all retained behavior is protected only for the new annotation-based contract.
- Mandatory Stop Condition: Build stops if it must preserve old subclass annotations, reveal Context to model input, change normal union semantics, or alter Strands protocol behavior.

## Protected Functionality
- Context values remain private to host and tool execution.
- A missing required Context cannot invoke the tool body.
- Unknown Context names fail before model execution proceeds.
- Context data is not serialized into standard tool input event payloads.
- Ordinary non-Context input behavior remains owned by the existing Pydantic model path.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/types.py` | `ToolContext` and new optional wrapper | Change public declaration semantics and define annotation metadata. | Current marker type is declared here. |
| `easyharness/_internal/tools.py` | Context parsing, schema creation, direct call binding | Normalize Context contracts, reject invalid syntax, and unify binding. | This file owns current recognition and invocation wrapping. |
| `easyharness/_internal/runtime.py` | Context contract aggregation and per-turn state | Consume normalized contracts and preserve unknown-name protection. | Runtime validates caller-provided Context names. |
| `easyharness/__init__.py` | Public export list | Export the new optional wrapper and updated type surface. | SDK public surface is centralized here. |
| `tests/test_sdk.py` | Context contract tests | Update fixtures and add registration, runtime, direct-call, signature, and privacy cases. | Existing tests exercise current Context behavior. |
| `README.md` and `tests/??.md` | Public examples and teaching material | Update only examples affected by the breaking annotation API. | Public and local guidance otherwise becomes stale. |

## Impact Scope Audit Findings
- The implementation boundary is localized to type declaration, tool contract parsing, runtime name aggregation, public exports, tests, and affected examples.
- No database, network, configuration, provider integration, or concurrency architecture change is expected.
- A source-scope expansion is permitted only when a directly affected public example or test fixture is discovered; it must be recorded before modification.

## Functional Boundary Conflict Readiness
- Escalation Trigger: A necessary implementation change conflicts with Context privacy, normal model-input semantics, the declared breaking boundary, or the no-legacy-support rule.
- Required Conflict Analysis: Identify the exact protected behavior, the minimal affected code surface, the incompatibility with D-001 or D-002, and whether a smaller compliant implementation exists.
- Recommended Option: Stop and request a user decision rather than adding a compatibility adapter.
- Decision Prompt: Present the conflict, the compliant stop path, and any explicitly scoped behavior-change alternative before continuing.
- Required Decision Record: Record the selected option, repository evidence, affected paths, compatibility outcome, and verification result in the execution log and state.
