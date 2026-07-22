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
from typing import Iterator, Mapping, cast

from strands import Agent as StrandsAgent
from strands.agent.conversation_manager import ConversationManager
from strands.types.content import Message

from easyharness._internal.conversation import (
    bind_event_sink_if_supported,
    clone_conversation_manager,
)
from easyharness._internal.model import build_runtime_model
from easyharness._internal.types import (
    AgentBusyError,
    AgentEvent,
    EventKind,
    EventStatus,
    ModelConfig,
)

_STREAM_END = object()


def _tool_public_name(tool_obj: object) -> str:
    """Return the public tool name used for default-tool de-duplication."""

    candidate = getattr(tool_obj, "tool_name", None)
    if isinstance(candidate, str) and candidate:
        return candidate
    if callable(candidate):
        value = candidate()
        if isinstance(value, str) and value:
            return value

    fallback = getattr(tool_obj, "__name__", None)
    if isinstance(fallback, str) and fallback:
        return fallback
    return tool_obj.__class__.__name__


def _merge_default_file_tools(
    *,
    tools: list[object] | None,
    enable_fileglide: bool,
) -> list[object]:
    """Merge explicit tools with the default fileglide toolset.

    Explicit tools keep precedence when a caller provides the same public tool
    name as one of the default file tools.
    """

    merged_tools = list(tools or [])
    if not enable_fileglide:
        return merged_tools

    from easyharness.toolset import build_fileglide_tools

    explicit_names = {_tool_public_name(item) for item in merged_tools}
    for default_tool in build_fileglide_tools():
        if _tool_public_name(default_tool) not in explicit_names:
            merged_tools.append(default_tool)
    return merged_tools


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


@dataclass(slots=True)
class _ToolPhaseState:
    """Track the active public tool phase for cancellation-aware finalization."""

    started_at: str
    started_monotonic: float
    name: str | None
    tool_use_id: str | None
    tool_input: object | None


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
        self._active_tools: dict[str, _ToolPhaseState] = dict()

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

    def _complete_tool_phase(
        self,
        *,
        status: EventStatus,
        tool_event: dict[str, object] | None = None,
        text: str | None = None,
    ) -> None:
        """Emit the terminal event for the currently tracked tool phase."""

        tool_use_id = (
            cast(str | None, tool_event.get("tool_use_id"))
            if tool_event is not None
            else None
        )
        tracked = (
            self._active_tools.pop(tool_use_id)
            if tool_use_id is not None
            else None
        )
        if tracked is None and tool_event is None:
            return

        started_at = (
            tracked.started_at
            if tracked is not None
            else cast(str | None, tool_event.get("started_at"))
        )
        duration_ms = (
            int((time.perf_counter() - tracked.started_monotonic) * 1000)
            if tracked is not None
            else cast(int | None, tool_event.get("duration_ms"))
        )
        name = (
            tracked.name
            if tracked is not None
            else cast(str | None, tool_event.get("name"))
        )
        public_tool_use_id = (
            tracked.tool_use_id
            if tracked is not None
            else tool_use_id
        )
        tool_input = (
            tracked.tool_input
            if tracked is not None
            else tool_event.get("input")
        )
        output = tool_event.get("output") if tool_event is not None else None

        self._emit(
            kind="tool",
            status=status,
            text=text,
            name=name,
            started_at=started_at,
            duration_ms=duration_ms,
            data={
                "tool_use_id": public_tool_use_id,
                "input": tool_input,
                "output": output,
            },
        )

    def _emit_system_cancelled(self, text: str | None = None) -> None:
        """Emit the final public system event for a cancelled invocation."""

        self._emit(
            kind="system",
            status="cancelled",
            text=text,
            started_at=utc_now_iso(),
            data={"stop_reason": "cancelled"},
        )

    def _handle_cancelled_result(self, result: object) -> None:
        """Convert a cancelled low-level result into public cancelled events."""

        final_text = _extract_message_text(getattr(result, "message", None)) or None
        if self._active_tools:
            for tool_use_id in list(self._active_tools):
                self._complete_tool_phase(
                    status="cancelled",
                    tool_event={"tool_use_id": tool_use_id},
                )
        elif self._assistant is not None:
            self._flush_assistant(status="cancelled")
        elif self._thinking is not None:
            self._flush_thinking(status="cancelled")

        self._emit_system_cancelled(final_text)

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
            marker = raw_event.get("tool_stream_event", dict()).get("data", dict())
            tool_event = marker.get("easyharness_tool")
            if tool_event:
                self._flush_thinking()
                status = cast(EventStatus, tool_event["status"])
                if status == "started":
                    tool_use_id = cast(str | None, tool_event.get("tool_use_id"))
                    if tool_use_id is not None:
                        self._active_tools[tool_use_id] = _ToolPhaseState(
                            started_at=cast(str, tool_event["started_at"]),
                            started_monotonic=time.perf_counter(),
                            name=cast(str | None, tool_event.get("name")),
                            tool_use_id=tool_use_id,
                            tool_input=tool_event.get("input"),
                        )
                    self._emit(
                        kind="tool",
                        status="started",
                        name=tool_event.get("name"),
                        started_at=tool_event.get("started_at"),
                        data={
                            "tool_use_id": tool_event.get("tool_use_id"),
                            "input": tool_event.get("input"),
                            "output": None,
                        },
                    )
                else:
                    self._complete_tool_phase(
                        status=status,
                        tool_event=tool_event,
                        text=tool_event.get("error")
                        or tool_event.get("output", dict()).get("preview")
                        or tool_event.get("output", dict()).get("model_text"),
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
            if getattr(result, "stop_reason", None) == "cancelled":
                self._handle_cancelled_result(result)
                return
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
        self._tool_context_contracts = self._build_tool_context_contracts()
        self._conversation_manager_template = conversation_manager
        self._agent: StrandsAgent
        self._conversation_manager: ConversationManager
        self._state_lock = threading.Lock()
        self._active_invocations = 0
        self.reset()

    def _build_tool_context_contracts(self) -> dict[str, object]:
        """Build the hidden Context payload contract for registered tools."""

        contracts: dict[str, object] = dict()
        for tool_obj in self._tools:
            for parameter in getattr(tool_obj, "context_parameters", ()):
                contract = parameter.payload_annotation
                existing = contracts.get(parameter.name)
                if existing is not None and existing != contract:
                    raise ValueError(
                        f"Context parameter {parameter.name} has "
                        "conflicting declarations"
                    )
                contracts[parameter.name] = contract
        return contracts

    def _invocation_state(
        self,
        tool_contexts: Mapping[str, object],
    ) -> dict[str, object]:
        """Create a private Context mapping that is not shared across invocations."""

        unknown_names = sorted(set(tool_contexts) - set(self._tool_context_contracts))
        if unknown_names:
            raise ValueError(
                f"Unknown tool Context parameters: {', '.join(unknown_names)}"
            )
        return {"_easyharness_tool_contexts": dict(tool_contexts)}

    def _begin_invocation(self) -> None:
        """Acquire the single-session permit or reject a reentrant invocation."""

        with self._state_lock:
            if self._active_invocations:
                raise AgentBusyError("Agent already has an active invocation")
            self._active_invocations = 1

    def _end_invocation(self) -> None:
        """Release the single-session permit after an invocation terminates."""

        with self._state_lock:
            self._active_invocations = 0

    def cancel(self) -> None:
        """Cancel the current invocation; remain a no-op while idle."""

        with self._state_lock:
            if self._active_invocations == 0:
                return
            active_agent = self._agent

        active_agent.cancel()

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
        """Rebuild the idle session and reject resets during active invocations."""

        with self._state_lock:
            if self._active_invocations:
                raise AgentBusyError("Agent cannot reset while an invocation is active")
            self._agent = self._create_agent()

    def run(self, prompt: str, **tool_contexts: object) -> str:
        """Run one synchronous session turn and return the final text.

        Args:
            prompt: User input for the current turn.

        Returns:
            Final assistant text for the current turn.
        """

        self._begin_invocation()
        try:
            invocation_state = self._invocation_state(tool_contexts)
            bind_event_sink_if_supported(self._conversation_manager, None)
            result = self._agent(
                prompt,
                invocation_state=invocation_state,
            )
            return str(result).strip()
        finally:
            bind_event_sink_if_supported(self._conversation_manager, None)
            self._end_invocation()

    def stream(self, prompt: str, **tool_contexts: object) -> Iterator[AgentEvent]:
        """Return the public event stream as a synchronous generator.

        Args:
            prompt: User input for the current turn.

        Yields:
            Unified `AgentEvent` objects.
        """

        self._begin_invocation()
        try:
            invocation_state = self._invocation_state(tool_contexts)
            output_queue: "queue.Queue[object]" = queue.Queue()

            def worker() -> None:
                mapper = _EventMapper(output_queue)

                async def runner() -> None:
                    bind_event_sink_if_supported(
                        self._conversation_manager,
                        mapper.emit_internal,
                    )
                    try:
                        async for raw_event in self._agent.stream_async(
                            prompt,
                            invocation_state=invocation_state,
                        ):
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
                    self._end_invocation()
                    output_queue.put(_STREAM_END)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
        except BaseException:
            self._end_invocation()
            raise

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
        enable_fileglide: Whether to auto-load the official fileglide toolset.
        conversation_manager: Optional custom conversation manager. The default
            summarizing manager is used when omitted.
    """

    def __init__(
        self,
        model: ModelConfig,
        system_prompt: str,
        tools: list[object] | None = None,
        enable_fileglide: bool = True,
        conversation_manager: ConversationManager | None = None,
    ) -> None:
        """Initialize a session-oriented agent."""

        self._runtime = _StrandsRuntime(
            model_config=model,
            system_prompt=system_prompt,
            tools=_merge_default_file_tools(
                tools=tools,
                enable_fileglide=enable_fileglide,
            ),
            conversation_manager=conversation_manager,
        )

    def run(self, prompt: str, **tool_contexts: object) -> str:
        """Run one turn and return the final text result.

        Args:
            prompt: User input for the current turn.

        Returns:
            Final assistant text output.
        """

        return self._runtime.run(prompt, **tool_contexts)

    def stream(self, prompt: str, **tool_contexts: object) -> Iterator[AgentEvent]:
        """Run one turn and return the unified event stream.

        Args:
            prompt: User input for the current turn.

        Yields:
            Unified `AgentEvent` objects.
        """

        yield from self._runtime.stream(prompt, **tool_contexts)

    def cancel(self) -> None:
        """Cancel the current invocation; do nothing while idle."""

        self._runtime.cancel()

    def reset(self) -> None:
        """Clear the current session state and start a new session."""

        self._runtime.reset()
