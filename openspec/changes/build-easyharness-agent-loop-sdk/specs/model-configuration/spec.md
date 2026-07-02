## ADDED Requirements

### Requirement: ModelConfig MUST use direct human-readable parameters
The SDK MUST provide a public `ModelConfig` that accepts direct, human-readable parameters rather than channel, profile, or environment indirection. `ModelConfig` MUST include `model`, `api_key`, `base_url`, `temperature`, `top_p`, and `seed`.

#### Scenario: Minimal model configuration
- **WHEN** a developer constructs `ModelConfig` with only `model` and `api_key`
- **THEN** the SDK MUST treat the configuration as valid and apply the documented defaults for other fields

### Requirement: ModelConfig MUST define stable defaults
`ModelConfig` MUST default `base_url` to `https://api.openai.com/v1`, `temperature` to `0.01`, `top_p` to `0.01`, and `seed` to `None`.

#### Scenario: OpenAI-compatible defaults apply
- **WHEN** a developer omits `base_url`, `temperature`, `top_p`, and `seed`
- **THEN** the SDK MUST use `https://api.openai.com/v1`, `0.01`, `0.01`, and `None` respectively

### Requirement: SDK MUST allow explicit base_url override
The SDK MUST allow developers to override `base_url` directly so OpenAI-compatible providers can be used without introducing a separate provider-profile abstraction.

#### Scenario: Developer targets a compatible endpoint
- **WHEN** a developer constructs `ModelConfig` with `base_url="https://api.deepseek.com/v1"`
- **THEN** the SDK MUST route model calls to that explicit base URL instead of the default OpenAI endpoint

### Requirement: SDK MUST NOT depend on environment-variable model resolution
The SDK MUST NOT require environment variables, environment names, channel maps, or provider-profile identifiers to construct or run a model configuration.

#### Scenario: Explicit parameters are sufficient
- **WHEN** a developer supplies `model`, `api_key`, and any needed optional overrides directly in code
- **THEN** the SDK MUST be able to construct the runtime model without reading environment-variable configuration
