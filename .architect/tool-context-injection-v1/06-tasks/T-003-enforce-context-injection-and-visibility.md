# Task: T-003-enforce-context-injection-and-visibility

## Metadata
- Document Type: Task
- Document ID: T-003
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Design Sources
- Source Design References: D-002, D-003
- Design Rule References: R-D002-002, R-D003-001, R-D003-002
- Prohibited New Concepts: global Context storage, DI containers, automatic factories, Context serialization

## Preconditions
The preceding tasks are complete and their behavior is covered by focused tests before this task changes adjacent runtime code.

## Functional Boundary
- Requested Functionality: Resolve required Context only for invoked tools, validate it, inject call kwargs, and produce safe failures.
- Protected Functionality: Model arguments, public event input shape, ToolOutput semantics, and user-function non-execution on invalid Context.
- Explicit Non-Goals: No persistent Agent or Tool Context, schema exposure, or user-output redaction.
- Compatibility Guarantees: Existing @tool, Agent.run(prompt), and Agent.stream(prompt) remain valid.
- Mandatory Stop Condition: Injection would require Context in schema/events/messages or unsafe errors containing Context data.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/tools.py and easyharness/_internal/runtime.py | Relevant SDK seam | Make the smallest approved change | Approved D-design evidence; scope may expand only by recorded evidence. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: The listed seam is the approved execution entry point.
- Scope Expansion Decision Rule: Expand only when repository evidence proves an adjacent caller, test, or document must change to preserve the approved boundary.
- Required Assessment and Record: Record evidence, compatibility impact, verification, and state/log update before proceeding.

## MUST DO
- M-T003-001: Implement only the approved task boundary and preserve ordinary-tool behavior.

## MUST NOT DO
- N-T003-001: Do not introduce global, Agent-held, Tool-held, or publicly observable Context state.

## Atomic Steps
1. Inspect the listed seam and its immediate callers/tests.
2. Implement the approved change without widening the public control plane.
3. Add focused regression evidence and record actual files changed.

## Functional Boundary Conflict Protocol
- Escalation Trigger: Repository facts require violating the mandatory stop condition or cannot preserve protected functionality.
- Required Conflict Analysis: Compare the requested result, protected behavior, affected callers, compatibility consequences, and verification required for each path.
- Recommended Option: `1` keep the approved hidden per-turn boundary.
- Recommendation Rationale: It preserves the approved design and existing SDK compatibility.
- Decision Prompt: Choose `1` to preserve the approved boundary or `2` to stop this plan and request a redesigned scope.
- Decision Limit: Stop implementation until the user selects a numbered path.
- Required Decision Record: Record the selected option, rationale, changed boundary, and verification in the execution log and centralized state.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- |
| 1 | Preserve approved boundary | Complete only compatible portion | Protects hidden per-turn Context | No unapproved API/state change | Focused tests and regression suite |
| 2 | Stop for redesign | Defers conflicting portion | Avoids accidental regression | Requires new approved design | User-approved revised plan and tests |

## Required Verification Evidence
- Verification Procedure: Run focused tests for the changed seam, then relevant existing SDK regression tests.
- Required Evidence: Passing test output, inspected event/schema behavior, and execution-log entry.

## Completion Criteria
The requested behavior works, protected behavior remains covered, no Context value crosses the public boundary, and recorded verification supports the task completion.
