"""Bridge from public model config to the Strands model runtime.

This module turns public `ModelConfig` values into a concrete
`LiteLLMModel`. The SDK relies only on explicit inputs and does not read
environment variables or introduce extra channel/profile indirection.
"""

from __future__ import annotations

from strands.models.litellm import LiteLLMModel

from .types import ModelConfig


def build_runtime_model(config: ModelConfig) -> LiteLLMModel:
    """Build the underlying LiteLLM model from public configuration.

    Args:
        config: Public SDK model configuration.

    Returns:
        A configured `LiteLLMModel` instance.
    """

    params: dict[str, object] = {
        "temperature": config.temperature,
        "top_p": config.top_p,
    }
    if config.seed is not None:
        params["seed"] = config.seed

    return LiteLLMModel(
        client_args={
            "api_key": config.api_key,
            "base_url": config.base_url,
        },
        model_id=config.model,
        params=params,
        stream=True,
    )
