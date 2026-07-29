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
from typing import Iterator, NoReturn

from strands import Agent as StrandsAgent
from strands.agent.conversation_manager import ConversationManager
from strands.types.content import ContentBlock, Message, Messages, ReasoningContentBlock
from strands.types.tools import ToolResult, ToolResultContent, ToolResultStatus, ToolUse

from easyharness._internal.conversation import (
    bind_event_sink_if_supported,
    clone_conversation_manager,
)
from easyharness._internal.model import build_runtime_model
from easyharness._internal.streaming import RuntimeSignal
from easyharness._internal.types import (
    AgentBusyError,
    AgentEvent,
    EventKind,
    EventOperation,
    ModelConfig,
)

_STREAM_END = object()
PromptInput = str | list[Mapping[str, object]]


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
    """Return the value only when it is a string."""

    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    """Return the value only when it is a non-boolean integer."""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


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
        """Convert supported text content into Strands tool-result blocks."""

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
    """Track one active public lifecycle phase."""

    phase_id: str
    kind: EventKind
    started_at: str
    started_monotonic: float
    data: Mapping[str, object] | None


class _EventMapper:
    """Project private runtime signals into canonical public events."""

    def __init__(self, output_queue: "queue.Queue[object]") -> None:
        """Initialize the projector state for one stream invocation."""

        self._output_queue = output_queue
        self._sequence = 0
        self._phase_number = 0
        self._phases: dict[tuple[str, str], _PhaseState] = {}
        self._finished_phase_keys: set[tuple[str, str]] = set()
        self._assistant_has_delta = False

    @staticmethod
    def _phase_key(signal: RuntimeSignal) -> tuple[str, str]:
        """Return the registry key for one private phase."""

        return signal.kind, signal.phase_key or signal.kind

    def _emit(
        self,
        phase: _PhaseState,
        operation: EventOperation,
        *,
        delta: str | None = None,
        error: str | None = None,
        duration_ms: int | None = None,
        data: Mapping[str, object] | None = None,
    ) -> None:
        """Create and queue one uniquely sequenced public event."""

        self._output_queue.put(
            AgentEvent(
                sequence=self._sequence,
                phase_id=phase.phase_id,
                kind=phase.kind,
                operation=operation,
                delta=delta,
                error=error,
                started_at=phase.started_at,
                duration_ms=duration_ms,
                data=data,
            )
        )
        self._sequence += 1

    def _start_phase(self, signal: RuntimeSignal) -> _PhaseState:
        """Start a phase once and return its active state."""

        key = self._phase_key(signal)
        phase = self._phases.get(key)
        if phase is not None:
            return phase

        self._phase_number += 1
        phase = _PhaseState(
            phase_id=f"{signal.kind}-{self._phase_number}",
            kind=signal.kind,
            started_at=signal.started_at or utc_now_iso(),
            started_monotonic=time.perf_counter(),
            data=signal.data,
        )
        self._phases[key] = phase
        self._finished_phase_keys.discard(key)
        self._emit(phase, "started", data=signal.data)
        return phase

    def finish_phase(self, signal: RuntimeSignal) -> None:
        """Finish one phase through the only terminal-event path."""

        key = self._phase_key(signal)
        phase = self._phases.pop(key, None)
        if phase is None:
            if key in self._finished_phase_keys:
                return
            phase = self._start_phase(signal)
            self._phases.pop(key, None)

        self._finished_phase_keys.add(key)
        duration_ms = signal.duration_ms
        if duration_ms is None:
            duration_ms = int((time.perf_counter() - phase.started_monotonic) * 1000)
        self._emit(
            phase,
            signal.operation,
            error=signal.error if signal.operation == "failed" else None,
            duration_ms=duration_ms,
            data=signal.data if signal.data is not None else phase.data,
        )

    def project(self, signal: RuntimeSignal) -> None:
        """Project one adapted private signal."""

        if signal.operation == "started":
            self._start_phase(signal)
            return

        if signal.operation == "delta":
            if not signal.delta:
                return
            phase = self._start_phase(signal)
            if phase.kind == "assistant":
                self._assistant_has_delta = True
            self._emit(phase, "delta", delta=signal.delta, data=signal.data)
            return

        self.finish_phase(signal)

    def _finish_kind(
        self,
        kind: EventKind,
        operation: EventOperation,
        error: str | None = None,
    ) -> None:
        """Finish every active phase of one kind."""

        for key, phase in list(self._phases.items()):
            if phase.kind == kind:
                self.project(
                    RuntimeSignal(
                        source="runtime",
                        kind=kind,
                        operation=operation,
                        phase_key=key[1],
                        error=error,
                    )
                )

    def _emit_text_delta(self, kind: EventKind, delta: str) -> None:
        """Adapt one Strands text delta into private phase signals."""

        self.project(
            RuntimeSignal(
                source="strands",
                kind=kind,
                operation="started",
                phase_key=kind,
            )
        )
        self.project(
            RuntimeSignal(
                source="strands",
                kind=kind,
                operation="delta",
                phase_key=kind,
                delta=delta,
            )
        )

    def emit_internal(self, signal: RuntimeSignal) -> None:
        """Project a private signal emitted by the conversation manager."""

        self.project(signal)

    def feed(self, raw: Mapping[str, object]) -> None:
        """Adapt one raw Strands event and project it."""

        reasoning = _optional_str(raw.get("reasoningText"))
        if reasoning:
            self._finish_kind("assistant", "completed")
            self._emit_text_delta("thinking", reasoning)
            return

        if raw.get("type") == "tool_stream":
            stream_event = raw.get("tool_stream_event")
            signal = (
                stream_event.get("data")
                if isinstance(stream_event, Mapping)
                else None
            )
            if isinstance(signal, RuntimeSignal):
                self._finish_kind("thinking", "completed")
                self.project(signal)
            return

        delta = _optional_str(raw.get("data"))
        if delta:
            self._finish_kind("thinking", "completed")
            self._emit_text_delta("assistant", delta)
            return

        if "result" not in raw:
            return

        result = raw["result"]
        if getattr(result, "stop_reason", None) == "cancelled":
            self._finish_all("cancelled")
            self._emit_system("cancelled", data={"stop_reason": "cancelled"})
            return

        self._finish_kind("thinking", "completed")
        final_text = _extract_message_text(getattr(result, "message", None))
        if not self._assistant_has_delta and final_text:
            self._emit_text_delta("assistant", final_text)
        self._finish_kind("assistant", "completed")

    def _finish_all(self, operation: EventOperation, error: str | None = None) -> None:
        """Finish every active registered phase."""

        for key, phase in list(self._phases.items()):
            self.project(
                RuntimeSignal(
                    source="runtime",
                    kind=phase.kind,
                    operation=operation,
                    phase_key=key[1],
                    error=error,
                )
            )

    def _emit_system(
        self,
        operation: EventOperation,
        *,
        data: Mapping[str, object] | None = None,
        error: str | None = None,
    ) -> None:
        """Emit one invocation-level system lifecycle phase."""

        phase_key = f"system-{self._sequence}"
        self.project(
            RuntimeSignal(
                source="runtime",
                kind="system",
                operation="started",
                phase_key=phase_key,
            )
        )
        self.project(
            RuntimeSignal(
                source="runtime",
                kind="system",
                operation=operation,
                phase_key=phase_key,
                error=error,
                data=data,
            )
        )

    def finalize(self) -> None:
        """Finish active phases after a normal upstream end."""

        self._finish_all("completed")

    def fail(self, error: BaseException) -> None:
        """Fail active phases after an upstream exception."""

        message = str(error) or type(error).__name__
        self._finish_all("failed", message)
        self._emit_system("failed", error=message)


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
