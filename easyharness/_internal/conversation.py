"""Default conversation compression manager and event integration points.

This module adds a thin wrapper around Strands
`SummarizingConversationManager` so compression start, completion, and failure
emit unified upper-layer events without changing the original
reactive/proactive control-flow semantics.
"""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Protocol

from strands.agent.conversation_manager import (
    ConversationManager,
    ProactiveCompressionConfig,
    SummarizingConversationManager,
)

if TYPE_CHECKING:
    from strands.agent.agent import Agent as StrandsAgent

logger = logging.getLogger(__name__)

InternalEventSink = Callable[[dict[str, object]], None]
DEFAULT_PROACTIVE_COMPRESSION: ProactiveCompressionConfig = {
    "compression_threshold": 0.7,
}


class SupportsEventSink(Protocol):
    """Protocol for managers that optionally support event sink binding."""

    def bind_event_sink(self, sink: InternalEventSink | None) -> None:
        """Bind or clear an internal event sink."""


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""

    return datetime.now(timezone.utc).isoformat()


class EventingSummarizingConversationManager(SummarizingConversationManager):
    """Default summarizing conversation manager with compression events."""

    def __init__(
        self,
        summary_ratio: float = 0.3,
        preserve_recent_messages: int = 8,
        summarization_agent: StrandsAgent | None = None,
        summarization_system_prompt: str | None = None,
        *,
        pin_first: int | None = None,
        proactive_compression: bool | ProactiveCompressionConfig | None = (
            DEFAULT_PROACTIVE_COMPRESSION
        ),
        **kwargs: object,
    ) -> None:
        """Initialize the default summarizing conversation manager."""

        if isinstance(proactive_compression, dict):
            proactive_compression = deepcopy(proactive_compression)

        super().__init__(
            summary_ratio=summary_ratio,
            preserve_recent_messages=preserve_recent_messages,
            summarization_agent=summarization_agent,
            summarization_system_prompt=summarization_system_prompt,
            pin_first=pin_first,
            proactive_compression=proactive_compression,
            **kwargs,
        )
        self._event_sink: InternalEventSink | None = None

    def bind_event_sink(self, sink: InternalEventSink | None) -> None:
        """Bind or clear the runtime event sink.

        Args:
            sink: Callback for internal compression events; `None` unbinds it.
        """

        self._event_sink = sink

    def _emit(
        self,
        status: str,
        *,
        mode: str,
        started_at: str,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        """Emit an internal compression event to the upper layer."""

        if self._event_sink is None:
            return

        payload: dict[str, object] = {
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

    def reduce_context(
        self,
        agent: StrandsAgent,
        e: Exception | None = None,
        **kwargs: object,
    ) -> None:
        """Compress context and emit started/completed/failed events.

        Args:
            agent: Current Strands agent.
            e: Triggering exception; `None` means proactive compression.
            **kwargs: Reserved for compatibility with the underlying API.

        Raises:
            Exception: Propagated when reactive compression also fails.
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
            logger.warning(
                "Proactive summarization failed, continuing: %s",
                summarization_error,
            )
        else:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._emit(
                "completed",
                mode=mode,
                started_at=started_at,
                duration_ms=duration_ms,
            )


def clone_conversation_manager(
    conversation_manager: ConversationManager | None,
) -> ConversationManager:
    """Clone a conversation manager with the smallest practical cost.

    Args:
        conversation_manager: Caller-provided custom manager; falls back to the
            default summarizing manager when omitted.

    Returns:
        A conversation manager instance ready for the current session.
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
    """Bind an internal event sink when the manager supports it.

    Args:
        conversation_manager: Manager used by the current session.
        sink: Event sink to bind; `None` clears the binding.
    """

    binder = getattr(conversation_manager, "bind_event_sink", None)
    if callable(binder):
        binder(sink)
