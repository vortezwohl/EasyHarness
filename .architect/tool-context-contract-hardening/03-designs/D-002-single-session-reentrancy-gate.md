# Design: D-002-single-session-reentrancy-gate

## Metadata
- Document Type: Design
- Document ID: D-002
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Concept
- Canonical Name: Fail-Fast Single-Session Invocation Gate
- Category: Lifecycle and concurrency contract
- Reference: Monitor-style mutual exclusion

## Intent
Expose a stable AgentBusyError for reentry instead of leaking a Strands concurrency exception.

## Stable Core and Variation
- Stable Core: one Agent owns one mutable session and conversation manager.
- Variation: synchronous run and lazy stream consumption.
- Fixed Decision: permit one active invocation and fail fast on reentry.

## Repository Evidence
- Runtime has a state lock but permits a second entry to the dependency.
- A second call produces ConcurrencyException from Strands.

## Compatibility Boundary
- Preserve successful run, stream, cancel, and reset behavior.
- Export AgentBusyError from the root package.
- Reject active reset and a second active invocation; retain cancel.

## Pattern Decision
- GoF Decision: No pattern.
- Rationale: idle/busy is one invariant; State, Strategy, and Proxy add needless objects.

## External Evidence Decision
- Accepted: ownership of mutable sessions requires atomic exclusion.
- Rejected: queueing and per-call Agents change latency, cancellation, or session semantics.

## Rationale
Use the existing runtime lock for check-and-acquire and release, without holding it over model I/O.

## Alternatives
- Leak Strands exception: rejected.
- Queue calls: rejected.
- Create an Agent per call: rejected.

## Functional Boundary
- Requested Functionality: busy gate for run, consumed stream, and active reset.
- Protected Functionality: events, Context isolation, cancel, and session reuse.
- Explicit Non-Goals: queues, parallel sessions, schedulers, and dependency changes.
- Compatibility Guarantees: public methods and successful paths remain; one exception type is added.
- Mandatory Stop Condition: stop if a scheduler or a Strands concurrency-model change is required.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/runtime.py | invocation lifecycle | Busy acquisition, release, reset guard. | Dependency exception leaks. |
| easyharness/_internal/types.py | public exception | Define AgentBusyError. | Stable SDK contract. |
| easyharness/__init__.py | exports | Export AgentBusyError. | Root SDK surface. |
| tests/test_sdk.py | lifecycle tests | Reentry, reset, cancel, and release cases. | Boundary is untested. |

## Verification Seams
- A second run or consumed stream raises AgentBusyError.
- Active reset fails; cancel leaves the session reusable.
- Normal, exceptional, and worker-start failure release ownership.

## Counterexamples
Creating but not consuming a stream does not occupy the Agent; first consumption does, preserving lazy iteration.

## Anti-Patterns
- Counting unsupported concurrent calls.
- Holding a lock across model I/O.
- Changing only error text without a stable exception type.

## Rules
### MUST DO
- R-D002-001: Use the runtime lock for atomic check-and-acquire and one release path.
- R-D002-002: Define and root-export AgentBusyError and test its type.
- R-D002-003: Test run, stream, reset, cancel, and exceptional release paths.
### MUST NOT DO
- R-D002-N001: Do not queue, discard, or parallelize reentrant calls.
- R-D002-N002: Do not expose Strands ConcurrencyException as the SDK contract.
