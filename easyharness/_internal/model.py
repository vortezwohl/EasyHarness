"""Strands 模型桥接层。

本模块负责把公开 `ModelConfig` 转成底层 `LiteLLMModel`。SDK 只依赖显式
传入的参数，不读取环境变量，也不引入 channel/profile 之类的间接配置层。
"""

from __future__ import annotations

from strands.models.litellm import LiteLLMModel

from .types import ModelConfig


def build_runtime_model(config: ModelConfig) -> LiteLLMModel:
    """根据公开配置构造底层 LiteLLM 模型对象。

    Args:
        config: SDK 公开的模型配置。

    Returns:
        已配置好的 `LiteLLMModel` 实例。
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
