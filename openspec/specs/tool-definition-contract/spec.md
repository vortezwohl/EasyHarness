# tool-definition-contract Specification

## Purpose
TBD - created by archiving change build-easyharness-agent-loop-sdk. Update Purpose after archive.
## Requirements
### Requirement: SDK MUST provide a strict tool decorator
The SDK MUST provide a public `tool` decorator as the normal way to define tools for `Agent`. The decorator MUST require explicit values for `name`, `purpose`, `when_to_use`, `parameters`, `returns`, and `common_failures`.

#### Scenario: Required tool metadata is complete
- **WHEN** a developer defines a tool using the `tool` decorator
- **THEN** the SDK MUST reject the definition if any required metadata field is missing or empty

### Requirement: Tool documentation MUST align with function signatures
The SDK MUST require decorated tool functions to use typed parameters, and the documented `parameters` entries MUST align with the function signature. The SDK MUST reject tools whose documented parameter names and callable parameter names do not match.

#### Scenario: Parameter docs omit a callable parameter
- **WHEN** a decorated tool function has a parameter that is not covered by the declared `parameters` metadata
- **THEN** the SDK MUST reject the tool definition before runtime execution

#### Scenario: Parameter docs mention an unknown field
- **WHEN** a decorated tool documents a parameter name that is not present in the callable signature
- **THEN** the SDK MUST reject the tool definition before runtime execution

### Requirement: Tool contracts MUST remain language-agnostic
The SDK MUST enforce completeness and alignment of tool metadata, but it MUST NOT require metadata text to be English-only.

#### Scenario: Developer writes tool guidance in Chinese
- **WHEN** a developer provides complete tool metadata in Chinese
- **THEN** the SDK MUST accept the tool definition if the metadata and signature alignment rules are satisfied

### Requirement: SDK MUST expose ToolOutput as the advanced tool return type
The SDK MUST expose `ToolOutput` as a public return structure for tools that need structured model text and UI-facing summaries. `ToolOutput` MUST support `data`, `model_text`, `preview`, and `detail`.

#### Scenario: Tool returns structured output for model and UI
- **WHEN** a tool returns `ToolOutput(data=..., model_text=..., preview=..., detail=...)`
- **THEN** the SDK MUST preserve those fields for runtime execution and event emission

### Requirement: SDK MUST support simple tool return values
The SDK MUST allow a decorated tool to return a plain string or a serializable value without forcing every tool to construct `ToolOutput`.

#### Scenario: Tool returns a plain string
- **WHEN** a decorated tool returns a string
- **THEN** the SDK MUST treat that return value as a valid successful tool result without requiring manual `ToolOutput` construction

