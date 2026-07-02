"""默认会话压缩管理器及事件接入点。

本模块在 Strands 的 `SummarizingConversationManager` 上加一层极薄封装，
用于在压缩开始、完成、失败时向上层发出统一事件，而不改变底层原有的
reactive/proactive 控制流语义。
"""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from strands.agent.conversation_manager import ConversationManager, SummarizingConversationManager

logger = logging.getLogger(__name__)

InternalEventSink = Callable[[dict[str, Any]], None]


class SupportsEventSink(Protocol):
    """声明可选的事件 sink 绑定协议。"""

    def bind_event_sink(self, sink: InternalEventSink | None) -> None:
        """绑定或清空一个内部事件 sink。"""


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""

    return datetime.now(timezone.utc).isoformat()


class EventingSummarizingConversationManager(SummarizingConversationManager):
    """带压缩事件能力的默认摘要型会话管理器。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """初始化默认摘要型会话管理器。"""

        super().__init__(*args, **kwargs)
        self._event_sink: InternalEventSink | None = None

    def bind_event_sink(self, sink: InternalEventSink | None) -> None:
        """绑定或清空运行时事件 sink。

        Args:
            sink: 接收内部压缩事件的回调；传入 `None` 表示取消绑定。
        """

        self._event_sink = sink

    def _emit(self, status: str, *, mode: str, started_at: str, duration_ms: int | None = None, error: str | None = None) -> None:
        """向上层发出内部压缩事件。"""

        if self._event_sink is None:
            return

        payload: dict[str, Any] = {
            "easyharness_compress": {
                "status": status,
                "started_at": started_at,
                "duration_ms": duration_ms,
                "mode": mode,
            }
        }
        if error is not None:
            payload["easyharness_compress"]["error"] = error
        self._event_sink(payload)

    def reduce_context(self, agent: Any, e: Exception | None = None, **kwargs: Any) -> None:
        """执行上下文压缩并发出 started/completed/failed 事件。

        Args:
            agent: 当前 Strands Agent。
            e: 触发压缩的异常；为 `None` 时表示 proactive 压缩。
            **kwargs: 为兼容底层接口保留。

        Raises:
            Exception: reactive 压缩失败时继续向上传播原始失败。
        """

        del kwargs
        mode = "reactive" if e is not None else "proactive"
        started_at = utc_now_iso()
        start = time.perf_counter()
        self._emit("started", mode=mode, started_at=started_at)

        try:
            self._summarize_oldest(agent)
        except Exception as summarization_error:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._emit(
                "failed",
                mode=mode,
                started_at=started_at,
                duration_ms=duration_ms,
                error=str(summarization_error),
            )
            if e is not None:
                logger.error("Summarization failed: %s", summarization_error)
                raise summarization_error from e
            logger.warning("Proactive summarization failed, continuing: %s", summarization_error)
        else:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._emit("completed", mode=mode, started_at=started_at, duration_ms=duration_ms)


def clone_conversation_manager(
    conversation_manager: ConversationManager | None,
) -> ConversationManager:
    """按最小代价复制会话管理器，保证 reset 后能获得新会话状态。

    Args:
        conversation_manager: 调用方传入的自定义 manager；未传入时使用默认摘要型 manager。

    Returns:
        可供当前会话使用的会话管理器实例。
    """

    if conversation_manager is None:
        return EventingSummarizingConversationManager()

    try:
        return deepcopy(conversation_manager)
    except Exception:
        return conversation_manager


def bind_event_sink_if_supported(
    conversation_manager: ConversationManager,
    sink: InternalEventSink | None,
) -> None:
    """在支持时给 conversation manager 绑定内部事件 sink。

    Args:
        conversation_manager: 当前会话使用的 manager。
        sink: 要绑定的事件 sink；传入 `None` 表示清空。
    """

    binder = getattr(conversation_manager, "bind_event_sink", None)
    if callable(binder):
        binder(sink)
