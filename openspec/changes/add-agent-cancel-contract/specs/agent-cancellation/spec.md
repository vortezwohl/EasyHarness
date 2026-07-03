## ADDED Requirements

### Requirement: Agent MUST support explicit invocation cancellation
The SDK MUST allow a caller to cancel the current in-flight invocation through `Agent.cancel()`. This method MUST be safe to call from another thread or control context, MUST be idempotent across repeated calls, and MUST NOT require the caller to import internal runtime objects or the underlying Strands agent. If no invocation is currently active, `Agent.cancel()` MUST act as a no-op and MUST NOT corrupt the existing session state.

#### Scenario: Caller cancels a running stream invocation
- **WHEN** a developer starts `agent.stream(prompt)` and calls `agent.cancel()` before the invocation finishes
- **THEN** the current invocation MUST stop cooperatively without requiring direct access to internal runtime or provider objects

#### Scenario: Caller cancels while idle
- **WHEN** a developer calls `agent.cancel()` while the `Agent` has no active invocation
- **THEN** the call MUST complete without error and the existing conversation session MUST remain usable

### Requirement: Agent MUST remain reusable after cancellation
After an invocation is cancelled, the same `Agent` instance MUST remain valid for subsequent calls to `run(prompt)` or `stream(prompt)` unless the caller explicitly chooses to `reset()` it. Cancellation MUST stop only the current invocation and MUST NOT force a session rebuild as part of the public contract.

#### Scenario: Agent runs again after cancellation
- **WHEN** a developer cancels one invocation and then starts a new invocation on the same `Agent` instance
- **THEN** the new invocation MUST start normally without requiring an automatic `reset()`
