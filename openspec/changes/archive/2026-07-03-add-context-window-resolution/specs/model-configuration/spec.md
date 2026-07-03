## MODIFIED Requirements

### Requirement: ModelConfig MUST use direct human-readable parameters
The SDK MUST provide a public `ModelConfig` that accepts direct, human-readable parameters rather than channel, profile, or environment indirection. `ModelConfig` MUST include `model`, `api_key`, `base_url`, `temperature`, `top_p`, `seed`, and optional `context_window_limit`.

#### Scenario: Minimal model configuration
- **WHEN** a developer constructs `ModelConfig` with only `model` and `api_key`
- **THEN** the SDK MUST treat the configuration as valid and apply the documented defaults for other fields

### Requirement: ModelConfig MUST define stable defaults
`ModelConfig` MUST default `base_url` to `https://api.openai.com/v1`, `temperature` to `0.01`, `top_p` to `0.01`, `seed` to `None`, and `context_window_limit` to `None`.

#### Scenario: OpenAI-compatible defaults apply
- **WHEN** a developer omits `base_url`, `temperature`, `top_p`, `seed`, and `context_window_limit`
- **THEN** the SDK MUST use `https://api.openai.com/v1`, `0.01`, `0.01`, `None`, and `None` respectively
