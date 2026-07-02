# zero-arg-tool-support Specification

## Purpose
TBD - created by archiving change fix-deepseek-and-zero-arg-tools. Update Purpose after archive.
## Requirements
### Requirement: Zero-argument tool declarations
The SDK MUST allow a function with an empty signature to be declared as a tool with `parameters={}` while preserving the existing strict metadata contract for non-empty signatures.

#### Scenario: Empty signature accepts empty parameter mapping
- **WHEN** a developer decorates a zero-argument function with `@tool(..., parameters={})`
- **THEN** the SDK MUST create the tool successfully without requiring synthetic parameter documentation

#### Scenario: Non-empty signature still requires full parameter documentation
- **WHEN** a developer decorates a function that declares one or more parameters with `@tool(..., parameters={})`
- **THEN** the SDK MUST reject the declaration because the metadata does not match the function signature

