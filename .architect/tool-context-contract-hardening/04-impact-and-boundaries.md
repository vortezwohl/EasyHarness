# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Functional Boundary
- Requested Functionality: implement D-001 through D-003.
- Explicit Non-Goals: no queues, parallel sessions, grammar expansion, or Ruff configuration edits.
- Compatibility Obligations: preserve valid Context behavior, single-call events, cancel, stream, and session reuse; add AgentBusyError.
- Mandatory Stop Condition: stop if the work changes Strands concurrency semantics, user-owned changes, or valid Context behavior.

## Protected Functionality
- Context never enters model schemas and failed injection never invokes the tool body.
- Successful calls, cancellation, and session reuse remain intact.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/tools.py | Context compiler | Reject empty fixed tuple aliases. | Current branch accepts them. |
| easyharness/_internal/runtime.py | Invocation lifecycle | Add busy acquisition, release, and reset guard. | Dependency error currently leaks. |
| easyharness/_internal/types.py and __init__.py | Public exception | Define and export AgentBusyError. | Stable SDK error contract. |
| tests/test_sdk.py | Regression coverage | Add Context and lifecycle cases. | Boundaries are untested. |

## Impact Scope Audit Findings
- The known surface is limited to Context compilation, runtime lifecycle, public types, and SDK tests.
- tests/test_base.py performs a pre-existing real network call and is outside this plan.

## Functional Boundary Conflict Readiness
- If stream laziness cannot be preserved, compare first-consumption ownership, iterator-creation ownership, and stopping for a user decision.
- If rejecting only the approved annotation is impossible, list affected aliases and compatibility impact before a user decision.
