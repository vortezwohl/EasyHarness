# context-window-resolution Specification

## Purpose
TBD - created by archiving change add-context-window-resolution. Update Purpose after archive.
## Requirements
### Requirement: SDK MUST resolve context window limits before constructing the runtime model
The SDK MUST determine a concrete `context_window_limit` before constructing the runtime model used for agent execution. The resolution order MUST be: caller-supplied explicit value first, SDK-known model metadata second, and a final fallback value of `200000` last.

#### Scenario: Caller provides an explicit context window limit
- **WHEN** a developer constructs `ModelConfig(..., context_window_limit=131072)`
- **THEN** the SDK MUST use `131072` for the runtime model without replacing it through metadata lookup or fallback logic

#### Scenario: Known model uses SDK metadata lookup
- **WHEN** a developer omits `context_window_limit` and selects a model whose context window size is known to the SDK lookup path
- **THEN** the SDK MUST resolve and apply that known context window limit before runtime execution begins

#### Scenario: Unknown model falls back to the stable default
- **WHEN** a developer omits `context_window_limit` and the SDK cannot resolve a known model window size
- **THEN** the SDK MUST apply `200000` as the final runtime fallback

### Requirement: SDK MUST normalize provider-prefixed model identifiers during lookup
When the SDK attempts to resolve context window metadata from a model identifier, it MUST support provider-prefixed identifiers used by the public API, including the common `<provider>/<model>` form. The lookup path MUST avoid treating a known model as unknown solely because the public model string includes a provider prefix.

#### Scenario: OpenAI-prefixed model resolves through normalized lookup
- **WHEN** a developer constructs `ModelConfig(model=\"openai/gpt-4.1-mini\", ...)` without an explicit `context_window_limit`
- **THEN** the SDK MUST resolve the known context window limit for `gpt-4.1-mini` rather than falling back to `200000`

