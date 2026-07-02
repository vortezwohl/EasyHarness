## ADDED Requirements

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
