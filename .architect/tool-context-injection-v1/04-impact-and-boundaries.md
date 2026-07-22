# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Functional Boundary
Implement the ToolContext marker, signature classification, per-turn run/stream inputs, private invocation-state transport, injection validation, safe failure formatting, tests, and documentation. Do not add context_parameter configuration.

## Protected Functionality
Preserve strict metadata, ordinary Pydantic validation, zero-argument tools, direct calls, session reuse, cancellation, stream order, existing event shape, and all no-Context tool behavior.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/types.py | public marker | Define ToolContext | D-001 requires an empty marker. |
| easyharness/_internal/tools.py | _EasyHarnessTool | classify, validate, inject, safe errors | Existing signature and invocation seam. |
| easyharness/_internal/runtime.py | Agent and _StrandsRuntime | accept and forward state | Strands supports per-call state. |
| easyharness/__init__.py | exports | expose ToolContext | Additive public surface. |
| tests/test_sdk.py, README.md, openspec/specs | regression and contract docs | test and document | Required compatibility evidence. |

## Impact Scope Audit Findings
The scope covers definition, runtime, export, testing, and documentation. Build may expand only when evidence shows an adjacent caller, test, or documentation index is required; record the reason and verification without treating this table as a hard path limit.

## Functional Boundary Conflict Readiness
Stop if repository facts require Context in schema, messages, public events, or retained state. Present compatible hidden-boundary alternatives, impact, and verification before asking the user; do not silently use Agent/Tool fields or ContextVar.