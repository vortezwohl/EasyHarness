## ADDED Requirements

### Requirement: SDK MUST expose a minimal public surface
`easyharness` MUST expose exactly five primary top-level public names for normal SDK usage: `Agent`, `ModelConfig`, `AgentEvent`, `ToolOutput`, and `tool`. The SDK MUST NOT require callers to import registry objects, internal contract objects, runtime bridge types, or a parallel `Harness` entry point to build a working agent loop.

#### Scenario: Developer imports the SDK
- **WHEN** a developer follows the documented SDK quickstart
- **THEN** the developer MUST be able to build and run an agent loop by importing only `Agent`, `ModelConfig`, `AgentEvent`, `ToolOutput`, and `tool`

### Requirement: Agent MUST be the sole primary runtime entry point
The SDK MUST provide `Agent` as the single primary public runtime class. `Agent` SHALL be session-oriented and MUST preserve conversation state across multiple calls until `reset()` is invoked. `Agent` MUST support a direct result path through `run(prompt)` and an event-stream path through `stream(prompt)`.

#### Scenario: Session state persists across turns
- **WHEN** a developer calls `agent.run("first")` and then `agent.run("second")` without resetting the agent
- **THEN** the second turn MUST execute within the same conversation session rather than a fresh one-shot session

#### Scenario: Reset starts a new session
- **WHEN** a developer calls `agent.reset()` after one or more prior turns
- **THEN** subsequent turns MUST execute with a fresh conversation state

### Requirement: Internal SDK mechanics MUST remain encapsulated
The SDK MUST keep internal registries, bridge objects, provider adapters, validators, and event bus helpers behind private or internal modules. Public usage MUST NOT require callers to assemble those pieces manually.

#### Scenario: Normal usage does not require internal objects
- **WHEN** a developer constructs a standard `Agent`
- **THEN** the developer MUST NOT need to instantiate a registry, runtime bridge, or private contract object directly
