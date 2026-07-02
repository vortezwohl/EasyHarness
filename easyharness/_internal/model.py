"""Bridge from public model config to the Strands model runtime.

This module turns public `ModelConfig` values into a concrete
`LiteLLMModel`. The SDK relies only on explicit inputs and does not read
environment variables or introduce extra channel/profile indirection.
"""

from __future__ import annotations

import logging
from typing import Any

from strands.models.litellm import LiteLLMModel
from strands.models._validation import _has_location_source
from strands.types.content import ContentBlock, Messages, SystemContentBlock

from .types import ModelConfig

logger = logging.getLogger(__name__)


def _model_mentions_deepseek(model_id: str) -> bool:
    """Return whether the configured model name clearly targets DeepSeek."""

    normalized = model_id.strip().lower()
    if not normalized:
        return False
    if normalized.startswith("deepseek/"):
        return True
    if "/" in normalized:
        _, normalized = normalized.split("/", 1)
    return "deepseek" in normalized


def _base_url_targets_deepseek(base_url: str) -> bool:
    """Return whether the configured base URL points at DeepSeek."""

    return "api.deepseek.com" in base_url.strip().lower()


def _should_use_deepseek_compat(config: ModelConfig) -> bool:
    """Return whether the runtime should enable the DeepSeek compatibility path."""

    model_id = config.model.strip()
    provider = model_id.split("/", 1)[0].lower() if "/" in model_id else None

    if _model_mentions_deepseek(model_id):
        return True

    if provider not in (None, "openai"):
        return False

    return provider is None and _base_url_targets_deepseek(config.base_url)


def _extract_reasoning_text(contents: list[ContentBlock]) -> str | None:
    """Collapse reasoning text blocks into the string expected by DeepSeek."""

    chunks: list[str] = []
    for content in contents:
        reasoning = content.get("reasoningContent")
        if not reasoning:
            continue

        reasoning_text = reasoning.get("reasoningText")
        if reasoning_text and reasoning_text.get("text"):
            chunks.append(reasoning_text["text"])

    text = "".join(chunks).strip()
    return text or None


class _DeepSeekLiteLLMModel(LiteLLMModel):
    """Minimal LiteLLM variant that preserves DeepSeek tool-call reasoning."""

    @classmethod
    def _format_regular_messages(
        cls, messages: Messages, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Format messages without dropping reasoning tied to tool calls."""

        del kwargs
        formatted_messages: list[dict[str, Any]] = []

        for message in messages:
            contents = message["content"]

            filtered_contents = []
            for content in contents:
                if any(
                    block_type in content
                    for block_type in ["toolResult", "toolUse", "reasoningContent"]
                ):
                    continue
                if _has_location_source(content):
                    logger.warning(
                        "Location sources are not supported by OpenAI | skipping content block"
                    )
                    continue
                filtered_contents.append(content)

            formatted_contents = [
                cls.format_request_message_content(content)
                for content in filtered_contents
            ]
            formatted_tool_calls = [
                cls.format_request_message_tool_call(content["toolUse"])
                for content in contents
                if "toolUse" in content
            ]
            formatted_tool_messages = [
                cls.format_request_tool_message(content["toolResult"])
                for content in contents
                if "toolResult" in content
            ]

            formatted_message: dict[str, Any] = {
                "role": message["role"],
                **({"content": formatted_contents} if formatted_contents else {}),
                **({"tool_calls": formatted_tool_calls} if formatted_tool_calls else {}),
            }

            if message["role"] == "assistant" and formatted_tool_calls:
                reasoning_text = _extract_reasoning_text(contents)
                if reasoning_text is not None:
                    formatted_message["reasoning_content"] = reasoning_text
                    formatted_message.setdefault("content", "")

            formatted_messages.append(formatted_message)

            user_messages_with_images = []
            for tool_msg in formatted_tool_messages:
                tool_msg_clean, user_msg_with_images = cls._split_tool_message_images(
                    tool_msg
                )
                formatted_messages.append(tool_msg_clean)
                if user_msg_with_images:
                    user_messages_with_images.append(user_msg_with_images)
            formatted_messages.extend(user_messages_with_images)

        return formatted_messages

    @classmethod
    def format_request_messages(
        cls,
        messages: Messages,
        system_prompt: str | None = None,
        *,
        system_prompt_content: list[SystemContentBlock] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Format a DeepSeek-compatible messages array."""

        formatted_messages = cls._format_system_messages(
            system_prompt,
            system_prompt_content=system_prompt_content,
        )
        formatted_messages.extend(cls._format_regular_messages(messages, **kwargs))
        return [
            message
            for message in formatted_messages
            if "content" in message or "tool_calls" in message
        ]


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

    model_cls = (
        _DeepSeekLiteLLMModel
        if _should_use_deepseek_compat(config)
        else LiteLLMModel
    )

    return model_cls(
        client_args={
            "api_key": config.api_key,
            "base_url": config.base_url,
        },
        model_id=config.model,
        params=params,
        stream=True,
    )
