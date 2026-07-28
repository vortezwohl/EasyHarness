"""Session-oriented agent runtime for EasyHarness.

This module wraps the public `Agent` in a minimal synchronous interface while
reusing the Strands runtime, tool executor, and conversation manager under the
hood. It also maps lower-level callback events into stable `AgentEvent`
objects.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, NoReturn, cast

from strands import Agent as StrandsAgent
from strands.agent.conversation_manager import ConversationManager
from strands.types.content import ContentBlock, Message, Messages, ReasoningContentBlock
from strands.types.tools import ToolResult, ToolResultContent, ToolResultStatus, ToolUse

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
PromptInput = str | list[Mapping[str, object]]
_EVENT_STATUSES: tuple[EventStatus, ...] = (
    "started",
    "delta",
    "completed",
    "failed",
    "cancelled",
)


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


def _optional_str(value: object) -> str | None:
    """仅在值为字符串时返回，用于收窄低层事件的无类型字段。"""

    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    """仅在值为非布尔整数时返回，用于收窄低层事件的时长字段。"""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _event_status(value: object) -> EventStatus | None:
    """在发布前验证无类型内部事件状态是否符合公开 Literal 契约。"""

    if isinstance(value, str) and value in _EVENT_STATUSES:
        return cast(EventStatus, value)
    return None


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


def _normalize_prompt(prompt: PromptInput) -> Messages:
    """Convert supported public input into Strands message objects.

    The adapter accepts plain text and the text/function-tool subset of OpenAI
    Chat Completions history. Input system and developer messages remain
    invalid because system_prompt belongs to Agent construction.

    Optional provider metadata is ignored. Content that cannot be represented
    as Strands text or tool blocks fails explicitly instead of being discarded.

    Args:
        prompt: A single user message or a list of OpenAI-style messages.

    Returns:
        New Strands Messages without mutating caller-provided input.

    Raises:
        ValueError: The input contains an unsupported role or non-representable
            core message data.
    """

    def fail(index: int, field: str, reason: str) -> NoReturn:
        raise ValueError(f"Message at index {index} has invalid {field}: {reason}")

    def text_blocks(
        value: object,
        index: int,
        field: str,
    ) -> list[ContentBlock]:
        if isinstance(value, str):
            return [ContentBlock(text=value)]
        if not isinstance(value, list):
            fail(index, field, "must be str or a list of text parts")

        text_content_blocks: list[ContentBlock] = []
        for part_index, raw_part in enumerate(value):
            part_field = f"{field}[{part_index}]"
            if not isinstance(raw_part, Mapping):
                fail(index, part_field, "must be a mapping")

            part_type = raw_part.get("type")
            text = raw_part.get("text")
            if part_type not in (None, "text") or not isinstance(text, str):
                fail(index, part_field, "must be a text part")
            text_content_blocks.append(ContentBlock(text=text))
        return text_content_blocks

    def tool_input(
        value: object,
        index: int,
        field: str,
    ) -> dict[str, object]:
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                fail(index, field, "must be valid JSON object")
            if not isinstance(decoded, dict):
                fail(index, field, "must decode to a JSON object")
            return deepcopy(decoded)

        if isinstance(value, Mapping):
            return deepcopy(dict(value))

        fail(index, field, "must be a JSON object string or mapping")

    def tool_result_contents(
        value: object,
        index: int,
        field: str,
    ) -> list[ToolResultContent]:
        """将受支持的文本内容转换为 Strands 工具结果内容块。"""

        return [
            ToolResultContent(text=block["text"])
            for block in text_blocks(value, index, field)
        ]

    if isinstance(prompt, str):
        return [Message(role="user", content=[ContentBlock(text=prompt)])]
    if not isinstance(prompt, list):
        raise ValueError("prompt must be str or list of message mappings")

    messages: Messages = []
    for message_index, raw_message in enumerate(prompt):
        if not isinstance(raw_message, Mapping):
            fail(message_index, "message", "must be a mapping")

        role = raw_message.get("role")
        if not isinstance(role, str):
            fail(message_index, "role", "must be a str")
        if role in {"system", "developer"}:
            fail(
                message_index,
                "role",
                "cannot override or supplement system_prompt",
            )

        if role == "user":
            messages.append(
                Message(
                    role="user",
                    content=text_blocks(
                        raw_message.get("content"),
                        message_index,
                        "content",
                    ),
                )
            )
            continue

        if role == "assistant":
            content = raw_message.get("content")
            if content is None:
                message_blocks: list[ContentBlock] = []
            else:
                message_blocks = text_blocks(content, message_index, "content")

            reasoning_content = raw_message.get("reasoning_content")
            if isinstance(reasoning_content, str):
                message_blocks.append(
                    ContentBlock(
                        reasoningContent=ReasoningContentBlock(
                            reasoningText={"text": reasoning_content},
                        )
                    )
                )

            tool_calls = raw_message.get("tool_calls")
            if tool_calls is not None:
                if not isinstance(tool_calls, list):
                    fail(message_index, "tool_calls", "must be a list")
                for call_index, raw_call in enumerate(tool_calls):
                    call_path = f"tool_calls[{call_index}]"
                    if not isinstance(raw_call, Mapping):
                        fail(message_index, call_path, "must be a mapping")

                    call_type = raw_call.get("type")
                    if call_type is not None and call_type != "function":
                        fail(message_index, f"{call_path}.type", "must be function")

                    tool_use_id = raw_call.get("id")
                    function = raw_call.get("function")
                    if not isinstance(tool_use_id, str) or not tool_use_id:
                        fail(
                            message_index,
                            f"{call_path}.id",
                            "must be a non-empty str",
                        )
                    if not isinstance(function, Mapping):
                        fail(
                            message_index,
                            f"{call_path}.function",
                            "must be a mapping",
                        )

                    name = function.get("name")
                    if not isinstance(name, str) or not name:
                        fail(
                            message_index,
                            f"{call_path}.function.name",
                            "must be a non-empty str",
                        )
                    message_blocks.append(
                        ContentBlock(
                            toolUse=ToolUse(
                                toolUseId=tool_use_id,
                                name=name,
                                input=tool_input(
                                    function.get("arguments"),
                                    message_index,
                                    f"{call_path}.function.arguments",
                                ),
                            )
                        )
                    )

            if not message_blocks:
                fail(
                    message_index,
                    "message",
                    "assistant message must include representable content",
                )
            messages.append(Message(role="assistant", content=message_blocks))
            continue

        if role == "tool":
            tool_use_id = raw_message.get("tool_call_id")
            if not isinstance(tool_use_id, str) or not tool_use_id:
                fail(message_index, "tool_call_id", "must be a non-empty str")

            status: ToolResultStatus = (
                "error" if raw_message.get("status") == "error" else "success"
            )
            messages.append(
                Message(
                    role="user",
                    content=[
                        ContentBlock(
                            toolResult=ToolResult(
                                toolUseId=tool_use_id,
                                status=status,
                                content=tool_result_contents(
                                    raw_message.get("content"),
                                    message_index,
                                    "content",
                                ),
                            )
                        )
                    ],
                )
            )
            continue

        fail(message_index, "role", "only user, assistant, and tool are supported")

    return messages


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
        self, status: EventStatus = "completed", text_override: str | None = None
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
        self, status: EventStatus = "completed", text_override: str | None = None
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
        tool_event: Mapping[str, object] | None = None,
        text: str | None = None,
    ) -> None:
        """Emit the terminal event for the currently tracked tool phase."""

        tool_use_id = (
            _optional_str(tool_event.get("tool_use_id")) if tool_event else None
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
            else _optional_str(tool_event.get("started_at"))
        )
        duration_ms = (
            int((time.perf_counter() - tracked.started_monotonic) * 1000)
            if tracked is not None
            else _optional_int(tool_event.get("duration_ms"))
        )
        name = (
            tracked.name
            if tracked is not None
            else _optional_str(tool_event.get("name"))
        )
        public_tool_use_id = tracked.tool_use_id if tracked is not None else tool_use_id
        tool_input = (
            tracked.tool_input if tracked is not None else tool_event.get("input")
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
        status = _event_status(compress_event.get("status"))
        if status is None:
            return

        self._emit(
            kind="compress",
            status=status,
            started_at=_optional_str(compress_event.get("started_at")),
            duration_ms=_optional_int(compress_event.get("duration_ms")),
            text=_optional_str(compress_event.get("error")),
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

            chunk = _optional_str(raw_event.get("reasoningText")) or ""
            self._thinking.chunks.append(chunk)
            self._emit(
                kind="thinking",
                status="delta",
                text=chunk,
                started_at=self._thinking.started_at,
            )
            return

        if raw_event.get("type") == "tool_stream":
            stream_event = raw_event.get("tool_stream_event")
            if not isinstance(stream_event, Mapping):
                return
            marker = stream_event.get("data")
            if not isinstance(marker, Mapping):
                return
            tool_event = marker.get("easyharness_tool")
            if isinstance(tool_event, Mapping):
                self._flush_thinking()
                status = _event_status(tool_event.get("status"))
                if status is None:
                    return
                if status == "started":
                    tool_use_id = _optional_str(tool_event.get("tool_use_id"))
                    started_at = _optional_str(tool_event.get("started_at"))
                    name = _optional_str(tool_event.get("name"))
                    if tool_use_id is not None and started_at is not None:
                        self._active_tools[tool_use_id] = _ToolPhaseState(
                            started_at=started_at,
                            started_monotonic=time.perf_counter(),
                            name=name,
                            tool_use_id=tool_use_id,
                            tool_input=tool_event.get("input"),
                        )
                    self._emit(
                        kind="tool",
                        status="started",
                        name=name,
                        started_at=started_at,
                        data={
                            "tool_use_id": tool_event.get("tool_use_id"),
                            "input": tool_event.get("input"),
                            "output": None,
                        },
                    )
                else:
                    output = tool_event.get("output")
                    output_preview = (
                        _optional_str(output.get("preview"))
                        if isinstance(output, Mapping)
                        else None
                    )
                    output_model_text = (
                        _optional_str(output.get("model_text"))
                        if isinstance(output, Mapping)
                        else None
                    )
                    self._complete_tool_phase(
                        status=status,
                        tool_event=tool_event,
                        text=_optional_str(tool_event.get("error"))
                        or output_preview
                        or output_model_text,
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

            chunk = _optional_str(raw_event.get("data")) or ""
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
        self._conversation_manager: ConversationManager
        self._state_lock = threading.Lock()
        self._active_invocations = 0
        self._agent = self._create_agent()

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

    def run(self, prompt: PromptInput, **tool_contexts: object) -> str:
        """Run one synchronous session turn and return the final text.

        Args:
            prompt: User text or OpenAI Chat Completions text/function-tool
                message history.

        Returns:
            Final assistant text for the current turn.
        """

        self._begin_invocation()
        try:
            invocation_state = self._invocation_state(tool_contexts)
            messages = _normalize_prompt(prompt)
            bind_event_sink_if_supported(self._conversation_manager, None)
            result = self._agent(
                messages,
                invocation_state=invocation_state,
            )
            return str(result).strip()
        finally:
            bind_event_sink_if_supported(self._conversation_manager, None)
            self._end_invocation()

    def stream(
        self, prompt: PromptInput, **tool_contexts: object
    ) -> Iterator[AgentEvent]:
        """Return the public event stream as a synchronous generator.

        Args:
            prompt: User text or OpenAI Chat Completions text/function-tool
                message history.

        Yields:
            Unified `AgentEvent` objects.
        """

        self._begin_invocation()
        try:
            invocation_state = self._invocation_state(tool_contexts)
            messages = _normalize_prompt(prompt)
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
                            messages,
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
        conversation_manager: Optional custom conversation manager. When omitted,
            the session preserves its full history without automatic management.
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

    def run(self, prompt: PromptInput, **tool_contexts: object) -> str:
        """Run one turn and return the final text result.

        Args:
            prompt: User text or OpenAI Chat Completions text/function-tool
                message history.

        Returns:
            Final assistant text output.
        """

        return self._runtime.run(prompt, **tool_contexts)

    def stream(
        self, prompt: PromptInput, **tool_contexts: object
    ) -> Iterator[AgentEvent]:
        """Run one turn and return the unified event stream.

        Args:
            prompt: User text or OpenAI Chat Completions text/function-tool
                message history.

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
