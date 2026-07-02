# conversation-compression Specification

## Purpose
TBD - created by archiving change build-easyharness-agent-loop-sdk. Update Purpose after archive.
## Requirements
### Requirement: Agent MUST default to summarizing conversation management
When a developer does not supply a custom conversation manager, the SDK MUST use a summarizing conversation manager as the default conversation-reduction strategy for the agent session.

#### Scenario: Agent uses the default conversation manager
- **WHEN** a developer constructs an `Agent` without passing `conversation_manager`
- **THEN** the SDK MUST attach a summarizing conversation manager by default

### Requirement: SDK MUST allow custom conversation managers
The SDK MUST allow a developer to pass a custom conversation manager object to `Agent` instead of forcing the SDK default.

#### Scenario: Developer provides a custom manager
- **WHEN** a developer constructs `Agent(..., conversation_manager=custom_manager)`
- **THEN** the SDK MUST use the provided conversation manager for the session instead of instantiating the default manager

### Requirement: Context compression MUST emit reusable runtime events
The SDK MUST emit reusable compression events through the same underlying event mechanism used for other runtime activity. The compression event family MUST include `compress_started`, `compress_completed`, and `compress_failed`.

#### Scenario: Compression starts
- **WHEN** the default conversation manager begins context compression
- **THEN** the runtime MUST emit a compression-started event through the unified event mechanism

#### Scenario: Compression completes
- **WHEN** the default conversation manager successfully finishes context compression
- **THEN** the runtime MUST emit a compression-completed event through the unified event mechanism

#### Scenario: Compression fails
- **WHEN** the default conversation manager fails during context compression
- **THEN** the runtime MUST emit a compression-failed event through the unified event mechanism

### Requirement: Public stream MUST expose compression events as AgentEvent
Compression activity MUST be surfaced to upper layers as public `AgentEvent` values whose kind is `compress` and whose status reflects `started`, `completed`, or `failed`, so TUI and WebUI consumers can react directly without inferring compression behavior.

#### Scenario: UI consumes compression activity
- **WHEN** the runtime emits internal compression lifecycle events
- **THEN** `agent.stream(...)` MUST surface corresponding public `AgentEvent(kind="compress", ...)` items

### Requirement: Compression failure semantics MUST preserve underlying runtime behavior
The SDK MUST preserve the underlying conversation-manager control-flow semantics for reactive and proactive compression failures while still emitting failure events.

#### Scenario: Reactive compression fails during overflow recovery
- **WHEN** compression is triggered reactively during overflow recovery and summarization fails
- **THEN** the SDK MUST emit a compression-failed event and MUST continue to surface the failure to the caller

#### Scenario: Proactive compression fails
- **WHEN** compression is triggered proactively and summarization fails
- **THEN** the SDK MUST emit a compression-failed event without forcing the SDK to misreport the failure as a successful compression completion

