"""Session-oriented agent runtime for EasyHarness.

This module wraps the public `Agent` in a minimal synchronous interface while
reusing the Strands runtime, tool executor, and conversation manager under the
hood. It also maps lower-level callback events into stable `AgentEvent`
objects.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, cast

from strands import Agent as StrandsAgent
from strands.agent.conversation_manager import ConversationManager
from strands.types.content import Message

from .conversation import bind_event_sink_if_supported, clone_conversation_manager
from .model import build_runtime_model
from .types import AgentEvent, EventKind, EventStatus, ModelConfig

_STREAM_END = object()


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""

    return datetime.now(timezone.utc).isoformat()


def _extract_message_text(message: Message | None) -> str:
    """Extract readable text from a Strands message."""

    if not message:
        return ""

    chunks: list[str] = []
    for block in message.get("content", []):
        if "text" in block and block["text"]:
            chunks.append(block["text"])
        elif "citationsContent" in block:
            for item in block["citationsContent"].get("content", []):
                if "text" in item and item["text"]:
                    chunks.append(item["text"])
    return "\n".join(chunks).strip()


@dataclass(slots=True)
class _PhaseState:
    """Track phase start state and accumulated text for one stream phase."""

    started_at: str
    started_monotonic: float
    chunks: list[str]


class _EventMapper:
    """Map low-level runtime events into public `AgentEvent` objects."""

    def __init__(self, output_queue: "queue.Queue[object]") -> None:
        """Initialize the event mapper.

        Args:
            output_queue: Event queue consumed by the synchronous caller.
        """

        self._output_queue = output_queue
        self._thinking: _PhaseState | None = None
        self._assistant: _PhaseState | None = None

    def _emit(
        self,
        *,
        kind: EventKind,
        status: EventStatus,
        text: str | None = None,
        name: str | None = None,
        started_at: str | None = None,
        duration_ms: int | None = None,
        data: object | None = None,
    ) -> None:
        """Push one public event into the output queue."""

        self._output_queue.put(
            AgentEvent(
                kind=kind,
                status=status,
                text=text,
                name=name,
                started_at=started_at,
                duration_ms=duration_ms,
                data=data,
            )
        )

    @staticmethod
    def _start_phase() -> _PhaseState:
        """Create a fresh phase state object."""

        return _PhaseState(
            started_at=utc_now_iso(),
            started_monotonic=time.perf_counter(),
            chunks=[],
        )

    def _flush_thinking(
        self, status: str = "completed", text_override: str | None = None
    ) -> None:
        """Finish the thinking phase and emit its terminal event."""

        if self._thinking is None:
            return

        text = (
            text_override
            if text_override is not None
            else "".join(self._thinking.chunks)
        )
        duration_ms = int(
            (time.perf_counter() - self._thinking.started_monotonic) * 1000
        )
        self._emit(
            kind="thinking",
            status=status,
            text=text or None,
            started_at=self._thinking.started_at,
            duration_ms=duration_ms,
        )
        self._thinking = None

    def _flush_assistant(
        self, status: str = "completed", text_override: str | None = None
    ) -> None:
        """Finish the assistant phase and emit its terminal event."""

        if self._assistant is None:
            return

        text = (
            text_override
            if text_override is not None
            else "".join(self._assistant.chunks)
        )
        duration_ms = int(
            (time.perf_counter() - self._assistant.started_monotonic) * 1000
        )
        self._emit(
            kind="assistant",
            status=status,
            text=text or None,
            started_at=self._assistant.started_at,
            duration_ms=duration_ms,
        )
        self._assistant = None

    def emit_internal(self, payload: dict[str, object]) -> None:
        """Handle internal events pushed directly by the conversation manager."""

        compress_event = payload.get("easyharness_compress")
        if not isinstance(compress_event, dict):
            return
        compress_event = cast(dict[str, object], compress_event)

        self._emit(
            kind="compress",
            status=compress_event["status"],
            started_at=compress_event.get("started_at"),
            duration_ms=compress_event.get("duration_ms"),
            text=compress_event.get("error"),
            data={"mode": compress_event.get("mode")},
        )

    def feed(self, raw_event: dict[str, object]) -> None:
        """Consume a single low-level event.

        Args:
            raw_event: Raw event dictionary produced by Strands `stream_async`.
        """

        if "reasoningText" in raw_event:
            if self._thinking is None:
                self._flush_assistant()
                self._thinking = self._start_phase()
                self._emit(
                    kind="thinking",
                    status="started",
                    started_at=self._thinking.started_at,
                )

            chunk = raw_event.get("reasoningText") or ""
            self._thinking.chunks.append(chunk)
            self._emit(
                kind="thinking",
                status="delta",
                text=chunk,
                started_at=self._thinking.started_at,
            )
            return

        if raw_event.get("type") == "tool_stream":
            marker = raw_event.get("tool_stream_event", {}).get("data", {})
            tool_event = marker.get("easyharness_tool")
            if tool_event:
                self._flush_thinking()
                self._emit(
                    kind="tool",
                    status=tool_event["status"],
                    text=tool_event.get("error")
                    or tool_event.get("output", {}).get("preview")
                    or tool_event.get("output", {}).get("model_text"),
                    name=tool_event.get("name"),
                    started_at=tool_event.get("started_at"),
                    duration_ms=tool_event.get("duration_ms"),
                    data={
                        "tool_use_id": tool_event.get("tool_use_id"),
                        "input": tool_event.get("input"),
                        "output": tool_event.get("output"),
                    },
                )
            return

        if "data" in raw_event:
            if self._assistant is None:
                self._flush_thinking()
                self._assistant = self._start_phase()
                self._emit(
                    kind="assistant",
                    status="started",
                    started_at=self._assistant.started_at,
                )

            chunk = raw_event.get("data") or ""
            self._assistant.chunks.append(chunk)
            self._emit(
                kind="assistant",
                status="delta",
                text=chunk,
                started_at=self._assistant.started_at,
            )
            return

        if "result" in raw_event:
            result = raw_event["result"]
            final_text = _extract_message_text(getattr(result, "message", None))
            if self._assistant is None and final_text:
                self._assistant = self._start_phase()
            self._flush_thinking()
            self._flush_assistant(text_override=final_text or None)
            return

        if raw_event.get("event_loop_throttled_delay") is not None:
            self._emit(
                kind="system",
                status="delta",
                text=(
                    f"tool/model throttled: {raw_event['event_loop_throttled_delay']}s"
                ),
                started_at=utc_now_iso(),
            )

    def finalize(self) -> None:
        """Flush any remaining phase state when the stream ends."""

        self._flush_thinking()
        self._flush_assistant()

    def fail(self, error: BaseException) -> None:
        """Emit failure events when the stream ends with an exception."""

        self._flush_thinking(status="failed", text_override=str(error))
        self._flush_assistant(status="failed", text_override=str(error))
        self._emit(
            kind="system",
            status="failed",
            text=str(error),
            started_at=utc_now_iso(),
        )


class _StrandsRuntime:
    """Minimal bridge from EasyHarness to the Strands runtime."""

    def __init__(
        self,
        *,
        model_config: ModelConfig,
        system_prompt: str,
        tools: list[object],
        conversation_manager: ConversationManager | None,
    ) -> None:
        """Initialize the internal runtime.

        Args:
            model_config: Public model configuration.
            system_prompt: System prompt for the session.
            tools: Public tool list.
            conversation_manager: Optional custom manager from the caller.
        """

        self._model_config = model_config
        self._system_prompt = system_prompt
        self._tools = list(tools)
        self._conversation_manager_template = conversation_manager
        self._agent: StrandsAgent
        self._conversation_manager: ConversationManager
        self.reset()

    def _create_agent(self) -> StrandsAgent:
        """Create a new underlying Strands agent."""

        self._conversation_manager = clone_conversation_manager(
            self._conversation_manager_template,
        )
        return StrandsAgent(
            model=build_runtime_model(self._model_config),
            system_prompt=self._system_prompt,
            tools=self._tools,
            conversation_manager=self._conversation_manager,
            callback_handler=None,
        )

    def reset(self) -> None:
        """Rebuild the underlying agent and clear session state."""

        self._agent = self._create_agent()

    def run(self, prompt: str) -> str:
        """Run one synchronous session turn and return the final text.

        Args:
            prompt: User input for the current turn.

        Returns:
            Final assistant text for the current turn.
        """

        bind_event_sink_if_supported(self._conversation_manager, None)
        result = self._agent(prompt)
        return str(result).strip()

    def stream(self, prompt: str) -> Iterator[AgentEvent]:
        """Return the public event stream as a synchronous generator.

        Args:
            prompt: User input for the current turn.

        Yields:
            Unified `AgentEvent` objects.
        """

        output_queue: "queue.Queue[object]" = queue.Queue()

        def worker() -> None:
            mapper = _EventMapper(output_queue)

            async def runner() -> None:
                bind_event_sink_if_supported(
                    self._conversation_manager,
                    mapper.emit_internal,
                )
                try:
                    async for raw_event in self._agent.stream_async(prompt):
                        mapper.feed(raw_event)
                    mapper.finalize()
                finally:
                    bind_event_sink_if_supported(self._conversation_manager, None)

            try:
                asyncio.run(runner())
            except BaseException as error:
                mapper.fail(error)
                output_queue.put(error)
            finally:
                output_queue.put(_STREAM_END)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = output_queue.get()
            if item is _STREAM_END:
                break
            if isinstance(item, BaseException):
                raise item
            yield item


class Agent:
    """Single public entry point exposed to EasyHarness callers.

    Args:
        model: Public model configuration.
        system_prompt: System prompt used by the current session.
        tools: Tools available to the current agent.
        conversation_manager: Optional custom conversation manager; the default
            summarizing manager is used when omitted.
    """

    def __init__(
        self,
        model: ModelConfig,
        system_prompt: str,
        tools: list[object] | None = None,
        conversation_manager: ConversationManager | None = None,
    ) -> None:
        """Initialize a session-oriented agent."""

        self._runtime = _StrandsRuntime(
            model_config=model,
            system_prompt=system_prompt,
            tools=tools or [],
            conversation_manager=conversation_manager,
        )

    def run(self, prompt: str) -> str:
        """Run one turn and return the final text result.

        Args:
            prompt: User input for the current turn.

        Returns:
            Final assistant text output.
        """

        return self._runtime.run(prompt)

    def stream(self, prompt: str) -> Iterator[AgentEvent]:
        """Run one turn and return the unified event stream.

        Args:
            prompt: User input for the current turn.

        Yields:
            Unified `AgentEvent` objects.
        """

        yield from self._runtime.stream(prompt)

    def reset(self) -> None:
        """Clear the current session state and start a new session."""

        self._runtime.reset()
