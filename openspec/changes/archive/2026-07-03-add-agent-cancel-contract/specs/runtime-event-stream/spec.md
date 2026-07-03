## MODIFIED Requirements

### Requirement: AgentEvent MUST expose stable high-level runtime semantics
`AgentEvent` MUST expose high-level runtime semantics for at least `thinking`, `tool`, `assistant`, `compress`, and `system` event kinds. Each event MUST expose a status compatible with `started`, `delta`, `completed`, `failed`, or `cancelled`, along with timing and extensible detail fields.

#### Scenario: Assistant output streams incrementally
- **WHEN** the runtime produces a streaming assistant response
- **THEN** the public stream MUST emit `AgentEvent` items whose kind is `assistant`, whose status includes `delta`, and whose text reflects streamed response content

#### Scenario: Active phase is cancelled explicitly
- **WHEN** a running invocation is cancelled while a public phase such as `thinking`, `assistant`, or `tool` is active
- **THEN** the event stream MUST surface a terminal `AgentEvent` for that same phase whose status is `cancelled`

## ADDED Requirements

### Requirement: SDK MUST surface cancellation as a final public stream outcome
When an invocation is cancelled, `agent.stream(prompt)` MUST expose that stop condition as a stable public outcome rather than forcing upper layers to infer cancellation from raw provider text or missing events. The final public stream outcome MUST include a `system` event whose status is `cancelled`, and that event MUST carry enough structured detail for upper layers to identify the stop reason as cancellation.

#### Scenario: Cancelled invocation reaches stream terminus
- **WHEN** a developer cancels an invocation consumed through `agent.stream(prompt)`
- **THEN** the event stream MUST emit a final `AgentEvent(kind="system", status="cancelled", ...)` before the stream ends

#### Scenario: Cancellation happens before a phase emits deltas
- **WHEN** a developer cancels an invocation before any public `thinking`, `assistant`, or `tool` delta event has been emitted
- **THEN** the stream MUST still expose cancellation through the final public `system` event rather than ending silently
