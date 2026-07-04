## ADDED Requirements

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
