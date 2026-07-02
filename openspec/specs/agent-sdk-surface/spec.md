# agent-sdk-surface Specification

## Purpose
TBD - created by archiving change build-easyharness-agent-loop-sdk. Update Purpose after archive.
## Requirements
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

### Requirement: Agent MUST load the official file toolset by default
`Agent` MUST automatically load the official fileglide-based file toolset unless the caller explicitly disables that behavior. The default loading behavior MUST use the SDK's official toolset builder rather than requiring the caller to manually pass the standard file tools.

#### Scenario: Default agent includes official file tools
- **WHEN** a developer constructs an `Agent` without disabling file tools
- **THEN** the agent MUST include the official fileglide-based file toolset in addition to any explicitly supplied tools

#### Scenario: Default loading does not require explicit toolset import
- **WHEN** a developer follows the standard `Agent` construction path
- **THEN** the SDK MUST provide the default official file tools without requiring the developer to import `easyharness.toolset`

### Requirement: Agent MUST support explicit disabling of default file tools
`Agent` MUST expose an explicit constructor parameter that allows callers to disable the default fileglide-based file toolset. When that parameter is disabled, the SDK MUST NOT auto-load the official file tools.

#### Scenario: Developer disables default file tools
- **WHEN** a developer constructs `Agent(..., enable_fileglide=False)`
- **THEN** the agent MUST omit the default official fileglide-based file toolset

#### Scenario: Developer disables defaults and passes custom tools
- **WHEN** a developer constructs `Agent(..., enable_fileglide=False, tools=[custom_tool])`
- **THEN** the agent MUST include the supplied custom tools without re-adding the default official file tools

### Requirement: Explicit caller tools MUST take precedence over default file tools
When the caller supplies explicit tools whose names collide with official default file tool names, the SDK MUST preserve the caller-supplied tool and MUST NOT activate a duplicate default tool with the same public name.

#### Scenario: Caller overrides a default official file tool
- **WHEN** a developer supplies a custom tool whose public name matches one of the official fileglide default tools
- **THEN** the agent MUST keep the caller-supplied tool active and MUST NOT register a conflicting duplicate default tool

