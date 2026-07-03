## MODIFIED Requirements

### Requirement: Agent MUST be the sole primary runtime entry point
The SDK MUST provide `Agent` as the single primary public runtime class. `Agent` SHALL be session-oriented and MUST preserve conversation state across multiple calls until `reset()` is invoked. `Agent` MUST support a direct result path through `run(prompt)`, an event-stream path through `stream(prompt)`, and an explicit cooperative stop path through `cancel()`.

#### Scenario: Session state persists across turns
- **WHEN** a developer calls `agent.run("first")` and then `agent.run("second")` without resetting the agent
- **THEN** the second turn MUST execute within the same conversation session rather than a fresh one-shot session

#### Scenario: Reset starts a new session
- **WHEN** a developer calls `agent.reset()` after one or more prior turns
- **THEN** subsequent turns MUST execute with a fresh conversation state

#### Scenario: Agent exposes explicit cancel control
- **WHEN** a developer uses the standard public `Agent` object during a running invocation
- **THEN** the developer MUST be able to request cancellation by calling `agent.cancel()` without importing internal runtime or framework objects
