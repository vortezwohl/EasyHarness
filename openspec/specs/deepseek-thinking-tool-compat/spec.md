# deepseek-thinking-tool-compat Specification

## Purpose
TBD - created by archiving change fix-deepseek-and-zero-arg-tools. Update Purpose after archive.
## Requirements
### Requirement: DeepSeek multi-turn thinking and tool-call compatibility
When the SDK is configured to call DeepSeek V4 through the OpenAI-compatible interface, it MUST preserve the reasoning context required for multi-turn thinking and tool-call continuity instead of routing that history through a formatter that drops the required reasoning content.

#### Scenario: Tool-call history preserves required reasoning context
- **WHEN** a DeepSeek-configured agent sends a follow-up request after an assistant turn that contained thinking content and a tool call
- **THEN** the SDK MUST format the request history so that the reasoning content required by that tool-call chain is preserved

#### Scenario: Non-DeepSeek models keep the default formatting path
- **WHEN** the SDK is configured for a model that is not identified as DeepSeek
- **THEN** the SDK MUST continue using the existing default LiteLLM formatting behavior

