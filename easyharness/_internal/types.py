"""EasyHarness 的公开数据结构定义。

本模块集中定义 SDK 对外可见的数据结构，包括模型配置、流式事件和高级工具
返回值。它们被运行时和工具合同共同复用，以保持公开语义稳定。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EventKind = Literal["thinking", "tool", "assistant", "compress", "system"]
EventStatus = Literal["started", "delta", "completed", "failed"]


@dataclass(slots=True, frozen=True)
class ModelConfig:
    """描述一次 Agent 会话所需的显式模型配置。

    Args:
        model: 直接传给底层模型的模型名。
        api_key: 当前模型请求使用的 API Key。
        base_url: OpenAI 兼容接口地址，默认指向 OpenAI 官方地址。
        temperature: 采样温度，默认保持极低波动。
        top_p: 核采样参数，默认保持极低波动。
        seed: 可选随机种子；未提供时保持底层默认行为。
    """

    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.01
    top_p: float = 0.01
    seed: int | None = None


@dataclass(slots=True, frozen=True)
class ToolOutput:
    """描述高级工具返回值，兼顾模型消费与 UI 展示。

    Args:
        data: 结构化原始数据，优先用于程序消费。
        model_text: 提供给模型继续推理的文本内容。
        preview: 提供给时间线或列表视图的简短预览。
        detail: 提供给详情面板或调试视图的扩展说明。
    """

    data: Any = None
    model_text: str | None = None
    preview: str | None = None
    detail: str | None = None


@dataclass(slots=True, frozen=True)
class AgentEvent:
    """统一的公开事件结构。

    Args:
        kind: 事件大类，例如 thinking、tool 或 assistant。
        status: 事件阶段，例如 started、delta、completed 或 failed。
        text: 当前事件对应的文本内容；对于 delta 事件通常是增量文本。
        name: 事件关联对象名，例如工具名。
        started_at: ISO 8601 时间戳，表示该阶段开始时间。
        duration_ms: 事件完成或失败时的持续毫秒数。
        data: 扩展负载，承载工具详情、压缩模式等附加信息。
    """

    kind: EventKind
    status: EventStatus
    text: str | None = None
    name: str | None = None
    started_at: str | None = None
    duration_ms: int | None = None
    data: Any = None
