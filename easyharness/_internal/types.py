"""Public data structures used by the EasyHarness SDK.

This module defines the externally visible structures for model configuration,
streaming events, and rich tool outputs. The runtime and tool contract logic
share these types to keep the public semantics stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EventKind = Literal["thinking", "tool", "assistant", "compress", "system"]
EventStatus = Literal["started", "delta", "completed", "failed", "cancelled"]


class ToolContext:
    """标记仅由宿主按回合注入的工具依赖类型。

    工具函数中标注为此类或其子类的参数不属于模型输入，因此不会出现在
    工具 schema、metadata 描述、模型消息或默认事件输入中。SDK 只识别
    类型标记，不负责构造、序列化、缓存或持有具体 Context 实例。
    """
    ...


@dataclass(slots=True, frozen=True)
class ModelConfig:
    """Explicit model settings for a single agent session.

    Args:
        model: Model name passed directly to the underlying client.
        api_key: API key used for requests made by this model.
        base_url: OpenAI-compatible endpoint, defaulting to the official URL.
        temperature: Sampling temperature with a deliberately low default.
        top_p: Nucleus sampling parameter with a deliberately low default.
        seed: Optional random seed; falls back to provider defaults when unset.
        context_window_limit: Optional explicit context window override used
            when the caller knows the real model capacity.
    """

    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.01
    top_p: float = 0.01
    seed: int | None = None
    context_window_limit: int | None = None


@dataclass(slots=True, frozen=True)
class ToolOutput:
    """Rich tool output for both model consumption and UI rendering.

    Args:
        data: Structured raw payload, primarily meant for programmatic use.
        model_text: Text fed back to the model for subsequent reasoning.
        preview: Short preview shown in timeline or list views.
        detail: Expanded details for inspector or debugging views.
    """

    data: object | None = None
    model_text: str | None = None
    preview: str | None = None
    detail: str | None = None


@dataclass(slots=True, frozen=True)
class AgentEvent:
    """Unified public event structure.

    Args:
        kind: Event category such as thinking, tool, or assistant.
        status: Event phase such as started, delta, completed, failed, or
            cancelled.
        text: Text attached to the event; usually incremental for delta events.
        name: Related object name, for example the tool name.
        started_at: ISO 8601 timestamp for when the phase started.
        duration_ms: Duration in milliseconds for completed, failed, or
            cancelled events.
        data: Extra payload carrying tool details, compression mode, and more.
    """

    kind: EventKind
    status: EventStatus
    text: str | None = None
    name: str | None = None
    started_at: str | None = None
    duration_ms: int | None = None
    data: object | None = None
