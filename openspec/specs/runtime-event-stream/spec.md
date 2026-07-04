# runtime-event-stream Specification

## Purpose
TBD - created by archiving change build-easyharness-agent-loop-sdk. Update Purpose after archive.
## Requirements
### Requirement: SDK MUST emit a unified event stream
The SDK MUST provide a unified event stream for runtime progress so upper layers can consume agent activity without inferring internal state transitions. The public stream API MUST yield `AgentEvent` objects rather than raw framework callbacks.

#### Scenario: Developer consumes stream events
- **WHEN** a developer iterates over `agent.stream(prompt)`
- **THEN** the iteration MUST yield `AgentEvent` objects that describe runtime progress in a stable SDK-defined shape

### Requirement: AgentEvent MUST expose stable high-level runtime semantics
`AgentEvent` MUST expose high-level runtime semantics for at least `thinking`, `tool`, `assistant`, `compress`, and `system` event kinds. Each event MUST expose a status compatible with `started`, `delta`, `completed`, `failed`, or `cancelled`, along with timing and extensible detail fields.

#### Scenario: Assistant output streams incrementally
- **WHEN** the runtime produces a streaming assistant response
- **THEN** the public stream MUST emit `AgentEvent` items whose kind is `assistant`, whose status includes `delta`, and whose text reflects streamed response content

#### Scenario: Active phase is cancelled explicitly
- **WHEN** a running invocation is cancelled while a public phase such as `thinking`, `assistant`, or `tool` is active
- **THEN** the event stream MUST surface a terminal `AgentEvent` for that same phase whose status is `cancelled`

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

### Requirement: SDK MUST surface cancellation as a final public stream outcome
When an invocation is cancelled, `agent.stream(prompt)` MUST expose that stop condition as a stable public outcome rather than forcing upper layers to infer cancellation from raw provider text or missing events. The final public stream outcome MUST include a `system` event whose status is `cancelled`, and that event MUST carry enough structured detail for upper layers to identify the stop reason as cancellation.

#### Scenario: Cancelled invocation reaches stream terminus
- **WHEN** a developer cancels an invocation consumed through `agent.stream(prompt)`
- **THEN** the event stream MUST emit a final `AgentEvent(kind="system", status="cancelled", ...)` before the stream ends

#### Scenario: Cancellation happens before a phase emits deltas
- **WHEN** a developer cancels an invocation before any public `thinking`, `assistant`, or `tool` delta event has been emitted
- **THEN** the stream MUST still expose cancellation through the final public `system` event rather than ending silently

### Requirement: Tool lifecycle events MUST remain correlated to their original invocation
When the runtime emits public `tool` events, each terminal event MUST stay correlated with the same tool invocation that emitted the matching `started` event. If multiple tool phases overlap, the SDK MUST correlate them by `tool_use_id` and MUST NOT source `name`, `input`, `started_at`, or duration data from a different active tool invocation.

#### Scenario: Overlapping same-name tools keep distinct identities
- **WHEN** one `tool.started` event for `tool-1` is followed by another `tool.started` event for `tool-2` with the same public tool name before `tool-1` reaches its terminal event
- **THEN** the eventual terminal public event for `tool-1` MUST retain `tool-1`'s original `tool_use_id`, `name`, `input`, and timing context

#### Scenario: Overlapping different tools do not relabel terminal events
- **WHEN** one tool invocation starts, a different tool invocation starts before the first one finishes, and the first invocation then emits a terminal event
- **THEN** the first invocation's public terminal event MUST NOT be relabeled with the second invocation's identity fields

### Requirement: Cancellation MUST close every active tool phase before stream termination
If an invocation is cancelled while one or more public tool phases are still active, the SDK MUST emit one terminal `tool.cancelled` event for each active tool invocation before emitting the final `system.cancelled` event.

#### Scenario: Cancellation closes multiple active tool phases
- **WHEN** an invocation is cancelled after multiple tool phases have emitted `started` but before all of them emit terminal events
- **THEN** the public stream MUST emit one `tool.cancelled` event per active `tool_use_id` before the final `system.cancelled` event

