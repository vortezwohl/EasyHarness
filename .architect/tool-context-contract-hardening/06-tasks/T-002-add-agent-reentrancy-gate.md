# Task: T-002-add-agent-reentrancy-gate

## Metadata
- Document Type: Task
- Document ID: T-002
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Design Sources
- Source Design References: D-002
- Design Rule References: R-D002-001, R-D002-002, R-D002-003, R-D002-N001, R-D002-N002
- Prohibited New Concepts: No queue, scheduler, parallel session, or Strands concurrency change.

## Preconditions
- D-002 is approved and FakeModel lifecycle fixtures remain available.

## Task Intent
Add the single-session fail-fast gate and public AgentBusyError.

## Functional Boundary
- Requested Functionality: a second active run, consumed stream, and active reset raise AgentBusyError.
- Protected Functionality: one run or stream, cancel, Context isolation, reuse, and reuse after failure.
- Explicit Non-Goals: queues, parallelism, per-call Agents, and Strands changes.
- Compatibility Guarantees: successful behavior and method signatures remain; one public exception is added.
- Mandatory Stop Condition: stop if a scheduler, long I/O lock, or dependency concurrency change is required.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/runtime.py | invocation lifecycle | Single permit, release, reset guard. | Dependency error leaks. |
| easyharness/_internal/types.py | exception type | Define AgentBusyError. | Stable SDK type. |
| easyharness/__init__.py | exports | Export exception. | Root capture surface. |
| tests/test_sdk.py | lifecycle tests | Reentry, reset, cancel, release. | State machine lacks coverage. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: runtime owns lifecycle and public types own stable errors.
- Scope Expansion Decision Rule: expand only for an adjacent release path or public exception requirement.
- Required Assessment and Record: record symbols, lock scope, terminal paths, and tests.

## MUST DO
- M-T002-001: Implement R-D002-001 atomic ownership and release.
- M-T002-002: Implement R-D002-002 public exception and type tests.
- M-T002-003: Implement R-D002-003 lifecycle tests.

## MUST NOT DO
- N-T002-001: Do not violate R-D002-N001 with queueing, discard, or parallelism.
- N-T002-002: Do not violate R-D002-N002 by leaking the dependency exception.

## Atomic Steps
1. Define occupancy and release for run and first stream consumption.
2. Define and export the exception and implement the gate.
3. Test reentry, reset, cancel, and release with FakeModel.
4. Run SDK tests and verify no dependency exception leaks.

## Functional Boundary Conflict Protocol
- Escalation Trigger: the gate cannot preserve stream laziness, cancel, and reuse together.
- Required Conflict Analysis: compare first-consumption ownership, iterator-creation ownership, and queueing with lifecycle effects.
- Recommended Option: `1`
- Recommendation Rationale: first-consumption ownership preserves lazy iteration and approved fail-fast behavior.
- Decision Prompt: Reply `1` for first-consumption ownership, `2` for iterator-creation ownership, or `3` to stop and reconsider concurrency.
- Decision Limit: this decides stream ownership timing only, not queueing or parallel sessions.
- Required Decision Record: record timing, scope, cancel effects, and tests.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Occupy at first stream consumption. | Implements fail-fast. | Preserves laziness. | Rejects only while active. | First-next stream test. |
| 2 | Occupy at iterator creation. | Fails earlier. | Changes unconsumed iterator behavior. | Requires approval. | Create, close, release tests. |
| 3 | Stop and redesign concurrency. | Does not implement request. | Current behavior remains. | No change. | Confirm no implementation change. |

## Required Verification Evidence
- Verification Procedure: hold one FakeModel call active, start another call or reset, then cancel or finish and retry.
- Required Evidence: stable busy type, no dependency error, and reuse after release.

## Completion Criteria
Reentry and active reset are rejected by the SDK; completion and cancellation leave the Agent reusable.
