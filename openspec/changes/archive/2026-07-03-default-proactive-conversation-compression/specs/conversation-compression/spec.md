## MODIFIED Requirements

### Requirement: Agent MUST default to summarizing conversation management
When a developer does not supply a custom conversation manager, the SDK MUST use a summarizing conversation manager as the default conversation-reduction strategy for the agent session. The default manager attached by EasyHarness MUST use SDK-owned defaults instead of inheriting opaque upstream defaults:

- proactive compression enabled with a default compression threshold of `0.7`
- `summary_ratio=0.3`
- `preserve_recent_messages=8`

#### Scenario: Agent uses the default conversation manager
- **WHEN** a developer constructs an `Agent` without passing `conversation_manager`
- **THEN** the SDK MUST attach a summarizing conversation manager by default
- **AND** that default manager MUST proactively compress context when projected input usage reaches `70%` of the configured context window
- **AND** that default manager MUST summarize using `summary_ratio=0.3`
- **AND** that default manager MUST preserve the most recent `8` messages before summarizing older context

## ADDED Requirements

### Requirement: Default eventing summarizing manager MUST allow explicit overrides
The SDK default eventing summarizing manager MUST continue to accept explicit constructor overrides for compression behavior so advanced callers can change the SDK defaults without replacing the entire manager implementation.

#### Scenario: Caller overrides proactive compression policy
- **WHEN** a caller constructs `EventingSummarizingConversationManager(proactive_compression=None)`
- **THEN** the manager MUST disable proactive compression for that instance instead of forcing the SDK default proactive policy

#### Scenario: Caller overrides summary retention values
- **WHEN** a caller constructs `EventingSummarizingConversationManager(summary_ratio=0.5, preserve_recent_messages=12)`
- **THEN** the manager MUST use `summary_ratio=0.5`
- **AND** the manager MUST preserve the most recent `12` messages for that instance instead of applying the SDK defaults

### Requirement: SDK MUST document the default compression policy
The SDK MUST document the default conversation compression behavior in the primary README so developers can understand when automatic summary may happen and how to override it.

#### Scenario: Developer reads the README
- **WHEN** a developer reads the SDK README to understand default runtime behavior
- **THEN** the README MUST state that EasyHarness uses a summarizing conversation manager by default
- **AND** the README MUST state that proactive compression is enabled by default
- **AND** the README MUST state that the default proactive compression threshold is `70%` of the context window
- **AND** the README MUST state that the default `summary_ratio` is `0.3`
- **AND** the README MUST state that the default `preserve_recent_messages` value is `8`
- **AND** the README MUST explain that callers can override the default compression policy by passing explicit manager parameters or a custom `conversation_manager`
