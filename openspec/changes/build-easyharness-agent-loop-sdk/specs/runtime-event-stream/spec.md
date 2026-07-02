## ADDED Requirements

### Requirement: SDK MUST emit a unified event stream
The SDK MUST provide a unified event stream for runtime progress so upper layers can consume agent activity without inferring internal state transitions. The public stream API MUST yield `AgentEvent` objects rather than raw framework callbacks.

#### Scenario: Developer consumes stream events
- **WHEN** a developer iterates over `agent.stream(prompt)`
- **THEN** the iteration MUST yield `AgentEvent` objects that describe runtime progress in a stable SDK-defined shape

### Requirement: AgentEvent MUST expose stable high-level runtime semantics
`AgentEvent` MUST expose high-level runtime semantics for at least `thinking`, `tool`, `assistant`, `compress`, and `system` event kinds. Each event MUST expose a status compatible with `started`, `delta`, `completed`, or `failed`, along with timing and extensible detail fields.

#### Scenario: Assistant output streams incrementally
- **WHEN** the runtime produces a streaming assistant response
- **THEN** the public stream MUST emit `AgentEvent` items whose kind is `assistant`, whose status includes `delta`, and whose text reflects streamed response content

### Requirement: SDK MUST measure thinking and tool durations automatically
The SDK MUST automatically measure thinking and tool execution timing and include that timing in emitted events so upper layers can render runtime durations without implementing their own timers.

#### Scenario: Tool execution completes
- **WHEN** a tool starts and later completes or fails
- **THEN** the emitted tool event sequence MUST include runtime timing information sufficient for a UI to show tool duration

### Requirement: SDK MUST keep event emission UI-agnostic
The SDK MUST emit runtime events without coupling them to a specific TUI, WebUI, timeline reducer, or layout policy.

#### Scenario: Different UIs consume the same runtime
- **WHEN** two different upper-layer consumers subscribe to the event stream
- **THEN** both consumers MUST be able to use the same `AgentEvent` objects without requiring a built-in EasyHarness UI component
