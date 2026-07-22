"""Minimal regression coverage for the EasyHarness SDK.

These tests prioritize the public surface, strict tool contracts, multi-turn
sessions, event streams, and compression events without falling back to internal
registries, bridges, or private contract objects.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import queue
import tempfile
import threading
import time
import unittest
from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol
from unittest import mock

from pydantic import BaseModel
from strands.agent.conversation_manager import ConversationManager
from strands.models.litellm import LiteLLMModel
from strands.models.model import Model
from strands.types.content import Messages, SystemContentBlock
from strands.types.exceptions import ContextWindowOverflowException
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

import easyharness
from easyharness import (
    Agent,
    AgentBusyError,
    ModelConfig,
    OptionalToolContext,
    ToolContext,
    ToolOutput,
    tool,
)
from easyharness._internal.conversation import (
    EventingSummarizingConversationManager,
    InternalEventSink,
    utc_now_iso,
)
from easyharness._internal.model import build_runtime_model
from easyharness._internal.runtime import _EventMapper, _StrandsRuntime


class _RequestContext:
    """Module-level Context payload used to verify hidden parameters."""

    def __init__(self, request_id: str) -> None:
        """Create a test Context with an identifier that must not leak by default."""

        self.request_id = request_id


class _DerivedRequestContext(_RequestContext):
    """Derived Context payload used to verify parent-class compatibility."""


class _AlternateRequestContext:
    """Alternate Context payload used to verify same-name contract conflicts."""


def _text_chunk(text: str) -> dict:
    """Build a minimal text streaming event."""

    return {"contentBlockDelta": {"delta": {"text": text}}}


class _AgentWithMessages(Protocol):
    """Declare the minimal agent message interface required by tests."""

    messages: Messages


class FakeModel(Model):
    """Minimal fake model used by SDK tests."""

    def __init__(
        self, *, overflow_threshold: int | None = None, fail_summary: bool = False
    ) -> None:
        """Initialize the test model.

        Args:
            overflow_threshold: Number of messages that triggers a context overflow.
            fail_summary: Whether summary requests should fail immediately.
        """

        self._config = {"context_window_limit": 128}
        self._overflow_threshold = overflow_threshold
        self._fail_summary = fail_summary

    def update_config(self, **model_config: object) -> None:
        """Update test configuration."""

        self._config.update(model_config)

    def get_config(self) -> dict[str, object]:
        """Return test configuration."""

        return self._config

    @property
    def context_window_limit(self) -> int:
        """Return the test model context window limit."""

        return int(self._config["context_window_limit"])

    async def structured_output(
        self,
        output_model: type[BaseModel],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[dict[str, object], None]:
        """The test model does not provide structured output."""

        del output_model, prompt, system_prompt, kwargs
        raise NotImplementedError

    async def count_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
    ) -> int:
        """Estimate token usage from the message count."""

        del tool_specs, system_prompt, system_prompt_content
        return len(messages) * 10

    @staticmethod
    def _latest_user_text(messages: Messages) -> str:
        """Extract the latest user text."""

        for message in reversed(messages):
            if message["role"] != "user":
                continue
            for block in message["content"]:
                if "text" in block:
                    return block["text"]
        return ""

    @staticmethod
    def _has_tool_result(messages: Messages) -> bool:
        """Return whether the current messages already contain a tool result."""

        return any(
            any("toolResult" in block for block in message["content"])
            for message in messages
        )

    @staticmethod
    def _has_summary_message(messages: Messages) -> bool:
        """Return whether the message history already contains a summary message."""

        return any(
            any(
                block.get("text") == "summary"
                for block in message["content"]
                if "text" in block
            )
            for message in messages
        )

    @staticmethod
    async def _emit_text_response(text: str) -> AsyncGenerator[StreamEvent, None]:
        """Emit one ordinary assistant text response."""

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": dict()}}
        yield _text_chunk(text)
        yield {"contentBlockStop": dict()}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 1,
                    "outputTokens": 1,
                    "totalTokens": 2,
                },
                "metrics": dict(),
            }
        }

    @staticmethod
    async def _emit_slow_text_response(
        *chunks: str,
        delay_before_first: float = 0.0,
        delay_between: float = 0.0,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Emit assistant text chunks at a controlled pace for cancellation tests."""

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": dict()}}
        if delay_before_first > 0:
            await asyncio.sleep(delay_before_first)
        for index, chunk in enumerate(chunks):
            yield _text_chunk(chunk)
            if delay_between > 0 and index < len(chunks) - 1:
                await asyncio.sleep(delay_between)
        yield {"contentBlockStop": dict()}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 1,
                    "outputTokens": 1,
                    "totalTokens": 2,
                },
                "metrics": dict(),
            }
        }

    @staticmethod
    async def _emit_tool_request() -> AsyncGenerator[StreamEvent, None]:
        """Emit a response containing reasoning content and a tool use request."""

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": dict()}}
        yield {
            "contentBlockDelta": {
                "delta": {"reasoningContent": {"text": "先调用工具"}},
            }
        }
        yield {"contentBlockStop": dict()}
        yield {
            "contentBlockStart": {
                "start": {
                    "toolUse": {
                        "toolUseId": "tool-1",
                        "name": "echo_tool",
                    }
                }
            }
        }
        yield {
            "contentBlockDelta": {
                "delta": {"toolUse": {"input": '{"text": "pong"}'}},
            }
        }
        yield {"contentBlockStop": dict()}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 1,
                    "outputTokens": 1,
                    "totalTokens": 2,
                },
                "metrics": dict(),
            }
        }

    def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, object] | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Return a minimal streaming event sequence based on input messages."""

        del tool_specs, tool_choice, system_prompt_content, invocation_state, kwargs

        async def generator() -> AsyncGenerator[StreamEvent, None]:
            if system_prompt and "conversation summarizer" in system_prompt.lower():
                if self._fail_summary:
                    raise RuntimeError("summary failed")
                async for event in self._emit_text_response("summary"):
                    yield event
                return

            if (
                self._overflow_threshold is not None
                and len(messages) > self._overflow_threshold
                and not self._has_summary_message(messages)
            ):
                raise ContextWindowOverflowException("overflow")

            latest_text = self._latest_user_text(messages)
            if self._has_tool_result(messages):
                async for event in self._emit_text_response("tool-result:done"):
                    yield event
                return

            if latest_text == "use_tool":
                async for event in self._emit_tool_request():
                    yield event
                return

            if latest_text == "slow_stream":
                async for event in self._emit_slow_text_response(
                    "slow-1",
                    "slow-2",
                    delay_between=0.2,
                ):
                    yield event
                return

            if latest_text == "slow_start":
                async for event in self._emit_slow_text_response(
                    "late",
                    delay_before_first=0.3,
                ):
                    yield event
                return

            user_turns = sum(1 for message in messages if message["role"] == "user")
            async for event in self._emit_text_response(
                f"turn:{user_turns} {latest_text}",
            ):
                yield event

        return generator()


class CustomConversationManager(ConversationManager):
    """Minimal implementation used to verify custom manager forwarding."""

    def __init__(self) -> None:
        """Initialize the custom manager."""

        super().__init__()
        self._event_sink: InternalEventSink | None = None

    def bind_event_sink(self, sink: InternalEventSink | None) -> None:
        """Bind an internal event sink."""

        self._event_sink = sink

    def apply_management(self, agent: object, **kwargs: object) -> None:
        """This test manager does not apply additional management."""

        del agent, kwargs

    def reduce_context(
        self,
        agent: _AgentWithMessages,
        e: Exception | None = None,
        **kwargs: object,
    ) -> None:
        """Compress context with custom behavior and emit a compression event."""

        del e, kwargs
        started_at = utc_now_iso()
        if self._event_sink:
            self._event_sink(
                {
                    "easyharness_compress": {
                        "status": "started",
                        "started_at": started_at,
                        "duration_ms": None,
                        "mode": "custom",
                    }
                }
            )
        agent.messages[:] = agent.messages[-2:]
        if self._event_sink:
            self._event_sink(
                {
                    "easyharness_compress": {
                        "status": "completed",
                        "started_at": started_at,
                        "duration_ms": 1,
                        "mode": "custom",
                    }
                }
            )


class EasyHarnessSdkTests(unittest.TestCase):
    """SDK regression test suite."""

    def test_public_surface_exports_only_expected_names(self) -> None:
        """The root public surface must export exactly the expected names."""

        self.assertEqual(
            set(easyharness.__all__),
            {
                "Agent",
                "AgentBusyError",
                "ModelConfig",
                "AgentEvent",
                "ToolContext",
                "OptionalToolContext",
                "ToolOutput",
                "tool",
            },
        )
        for name in easyharness.__all__:
            self.assertTrue(hasattr(easyharness, name))

    def test_tool_context_is_hidden_from_schema_and_metadata(self) -> None:
        """ToolContext parameters must remain private signature specifications."""

        @tool(
            name="contextual_greeting",
            purpose="生成带请求标识的问候语。",
            when_to_use="需要处理当前请求时使用。",
            parameters={"name": "需要问候的姓名。"},
            returns="问候语文本。",
            common_failures="姓名不能为空。",
        )
        def contextual_greeting(
            name: str,
            request: ToolContext[_RequestContext],
            optional_request: OptionalToolContext[_RequestContext],
        ) -> str:
            return f"{name}:{request.__class__.__name__}:{optional_request is None}"

        schema = contextual_greeting.tool_spec["inputSchema"]["json"]
        self.assertEqual(set(schema["properties"]), {"name"})
        self.assertNotIn("request", contextual_greeting.tool_spec["description"])
        self.assertEqual(
            contextual_greeting("Ada", _RequestContext("direct")),
            "Ada:_RequestContext:True",
        )

    def test_tool_context_metadata_remains_strict(self) -> None:
        """Context parameters must not enter metadata as ordinary model parameters."""

        with self.assertRaisesRegex(ValueError, "Unexpected parameter docs: request"):

            @tool(
                name="invalid_context_metadata",
                purpose="验证隐藏参数不能出现在 metadata。",
                when_to_use="仅用于测试。",
                parameters={"request": "不应接受的 Context 描述。"},
                returns="不会返回。",
                common_failures="注册失败。",
            )
            def invalid_context_metadata(request: ToolContext[_RequestContext]) -> str:
                return request.__class__.__name__

    def test_agent_injects_context_per_run_and_stream_without_event_leakage(
        self,
    ) -> None:
        """run and stream must inject Context per invocation without event leakage."""

        observed_request_ids: list[str] = []

        @tool(
            name="echo_tool",
            purpose="返回带有当前请求标识的结果。",
            when_to_use="模型需要验证 Context 注入时使用。",
            parameters={"text": "要回显的文本。"},
            returns="包含当前请求标识的输出。",
            common_failures="Context 注入失败。",
        )
        def echo_tool(text: str, request: ToolContext[_RequestContext]) -> ToolOutput:
            observed_request_ids.append(request.request_id)
            return ToolOutput(
                data={"text": text},
                model_text=text,
                preview=f"{text}:{request.request_id}",
            )

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                tools=[echo_tool],
                enable_fileglide=False,
            )
            run_result = agent.run("use_tool", request=_RequestContext("run-1"))
            agent.reset()
            events = list(agent.stream("use_tool", request=_RequestContext("stream-2")))

        self.assertEqual(run_result, "tool-result:done")
        self.assertEqual(observed_request_ids, ["run-1", "stream-2"])
        completed_event = next(
            event
            for event in events
            if event.kind == "tool" and event.status == "completed"
        )
        self.assertEqual(completed_event.data["input"], {"text": "pong"})
        self.assertNotIn("request", completed_event.data["input"])
        self.assertEqual(
            completed_event.data["output"]["preview"],
            "pong:stream-2",
        )

    def test_agent_context_validation_uses_safe_failures_and_rejects_unknown_names(
        self,
    ) -> None:
        """Invalid Context values must fail without executing tools."""

        call_count = 0

        @tool(
            name="echo_tool",
            purpose="验证 Context 失败行为。",
            when_to_use="仅用于测试。",
            parameters={"text": "要回显的文本。"},
            returns="不应在错误时返回。",
            common_failures="Context 不可用。",
        )
        def echo_tool(text: str, request: ToolContext[_RequestContext]) -> str:
            nonlocal call_count
            del text, request
            call_count += 1
            return "unexpected"

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                tools=[echo_tool],
                enable_fileglide=False,
            )
            missing_events = list(agent.stream("use_tool"))
            agent.reset()
            wrong_type_events = list(
                agent.stream("use_tool", request={"request_id": "secret-value"})
            )
            with self.assertRaisesRegex(ValueError, "Unknown tool Context parameters"):
                agent.run("plain", unknown=_RequestContext("not-used"))

        self.assertEqual(call_count, 0)
        for events in (missing_events, wrong_type_events):
            failed_event = next(
                event
                for event in events
                if event.kind == "tool" and event.status == "failed"
            )
            failure_text = str(failed_event.data)
            self.assertIn("request", failure_text)
            self.assertIn("_RequestContext", failure_text)
            self.assertNotIn("secret-value", failure_text)

    def test_tool_context_registration_rejects_legacy_and_ambiguous_declarations(
        self,
    ) -> None:
        """Context declarations must use one annotation-wrapped payload type."""

        with self.assertRaisesRegex(TypeError, "ToolContext cannot be subclassed"):

            class LegacyContext(ToolContext):
                pass

        with self.assertRaisesRegex(ValueError, "requires one concrete payload type"):

            @tool(
                name="invalid_context_payload_union",
                purpose="Validate Context contract rejection.",
                when_to_use="Use only in tests.",
                parameters=dict(),
                returns="No result is expected.",
                common_failures="The Context declaration is invalid.",
            )
            def invalid_context_payload_union(
                request: ToolContext[_RequestContext | _AlternateRequestContext],
            ) -> str:
                del request
                return "unexpected"

        with self.assertRaisesRegex(ValueError, "cannot use unions"):

            @tool(
                name="invalid_context_outer_union",
                purpose="Validate Context contract rejection.",
                when_to_use="Use only in tests.",
                parameters=dict(),
                returns="No result is expected.",
                common_failures="The Context declaration is invalid.",
            )
            def invalid_context_outer_union(
                request: ToolContext[_RequestContext] | _AlternateRequestContext,
            ) -> str:
                del request
                return "unexpected"

    def test_tool_context_registration_rejects_agent_reserved_names(self) -> None:
        """Registration must reject Context names reserved for Agent inputs."""

        with self.assertRaisesRegex(ValueError, "name 'prompt' is reserved"):

            @tool(
                name="invalid_prompt_context",
                purpose="Validate reserved Context name rejection.",
                when_to_use="Use only in tests.",
                parameters=dict(),
                returns="No result is expected.",
                common_failures="Registration must fail.",
            )
            def invalid_prompt_context(prompt: ToolContext[_RequestContext]) -> str:
                del prompt
                return "unexpected"

    def test_tool_context_registration_rejects_invalid_parameter_layouts(self) -> None:
        """Context declarations must use supported parameter kinds and ordering."""

        with self.assertRaisesRegex(ValueError, "positional-only"):

            @tool(
                name="invalid_positional_only_tool",
                purpose="Validate positional-only rejection.",
                when_to_use="Use only in tests.",
                parameters={"text": "Text input."},
                returns="No result is expected.",
                common_failures="Registration must fail.",
            )
            def invalid_positional_only_tool(text: str, /) -> str:
                return text

        with self.assertRaisesRegex(ValueError, "must follow ordinary positional"):

            @tool(
                name="invalid_context_order",
                purpose="Validate Context ordering rejection.",
                when_to_use="Use only in tests.",
                parameters={"text": "Text input."},
                returns="No result is expected.",
                common_failures="Registration must fail.",
            )
            def invalid_context_order(
                request: OptionalToolContext[_RequestContext],
                text: str,
            ) -> str:
                del request
                return text

        with self.assertRaisesRegex(ValueError, "Default for Context parameter"):

            @tool(
                name="invalid_context_default",
                purpose="Validate Context default rejection.",
                when_to_use="Use only in tests.",
                parameters=dict(),
                returns="No result is expected.",
                common_failures="Registration must fail.",
            )
            def invalid_context_default(
                request: ToolContext[_RequestContext] = _AlternateRequestContext(),
            ) -> str:
                del request
                return "unexpected"

    def test_optional_tool_context_uses_none_when_omitted(self) -> None:
        """Optional Context must resolve to None in runtime and direct calls."""

        @tool(
            name="optional_context_only",
            purpose="Validate optional Context defaults.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The observed Context default marker.",
            common_failures="The tool should not fail.",
        )
        def optional_context_only(
            request: OptionalToolContext[_RequestContext],
        ) -> str:
            return "default" if request is None else request.request_id

        self.assertEqual(optional_context_only(), "default")
        self.assertIsNone(
            inspect.signature(optional_context_only).parameters["request"].default
        )
        schema = optional_context_only.tool_spec["inputSchema"]["json"]
        self.assertEqual(schema.get("properties"), dict())

        async def invoke() -> list[object]:
            return [
                event
                async for event in optional_context_only.stream(
                    {"toolUseId": "tool-1", "input": dict()},
                    dict(),
                )
            ]

        events = asyncio.run(invoke())
        completed = next(
            event
            for event in events
            if isinstance(event, dict)
            and event.get("easyharness_tool", dict()).get("status") == "completed"
        )
        self.assertEqual(
            completed["easyharness_tool"]["output"]["model_text"],
            "default",
        )

    def test_concurrent_private_context_maps_do_not_leak_between_tool_invocations(
        self,
    ) -> None:
        """Concurrent tool calls must use separate private Context mappings."""

        observed_request_ids: list[str] = []

        @tool(
            name="concurrent_context_tool",
            purpose="验证并发 Context 隔离。",
            when_to_use="仅用于测试。",
            parameters={"text": "模型输入。"},
            returns="当前 Context 标识。",
            common_failures="不应失败。",
        )
        async def concurrent_context_tool(
            text: str, request: ToolContext[_RequestContext]
        ) -> str:
            await asyncio.sleep(0)
            observed_request_ids.append(f"{text}:{request.request_id}")
            return request.request_id

        async def invoke(text: str, request_id: str) -> None:
            async for _ in concurrent_context_tool.stream(
                {"toolUseId": text, "input": {"text": text}},
                {
                    "_easyharness_tool_contexts": {
                        "request": _RequestContext(request_id),
                    },
                },
            ):
                pass

        async def invoke_concurrently() -> None:
            await asyncio.gather(
                invoke("first", "ctx-1"),
                invoke("second", "ctx-2"),
            )

        asyncio.run(invoke_concurrently())
        self.assertEqual(set(observed_request_ids), {"first:ctx-1", "second:ctx-2"})

    def test_agent_rejects_conflicting_context_parameter_contracts(self) -> None:
        """Conflicting Context declarations must fail at Agent construction."""

        @tool(
            name="first_context_tool",
            purpose="定义第一个 Context 合同。",
            when_to_use="仅用于测试。",
            parameters=dict(),
            returns="不重要。",
            common_failures="不应失败。",
        )
        def first_context_tool(request: ToolContext[_RequestContext]) -> str:
            return request.request_id

        @tool(
            name="second_context_tool",
            purpose="定义冲突的 Context 合同。",
            when_to_use="仅用于测试。",
            parameters=dict(),
            returns="不重要。",
            common_failures="不应失败。",
        )
        def second_context_tool(request: ToolContext[_AlternateRequestContext]) -> str:
            del request
            return "second"

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "request has conflicting declarations",
            ):
                Agent(
                    model=ModelConfig(model="fake", api_key="fake"),
                    system_prompt="test",
                    tools=[first_context_tool, second_context_tool],
                    enable_fileglide=False,
                )

    def test_tool_context_deep_payload_validation_and_safe_failures(self) -> None:
        """Context payloads must validate nested containers without leaking values."""

        @tool(
            name="deep_context_tool",
            purpose="Validate deeply nested Context payloads.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The validated Context marker.",
            common_failures="The Context payload is invalid.",
        )
        def deep_context_tool(
            payload: ToolContext[dict[str, list[_RequestContext]]],
            marker: ToolContext[tuple[str, int]],
            labels: ToolContext[set[str]],
        ) -> str:
            return f"{payload['request'][0].request_id}:{marker[0]}:{len(labels)}"

        self.assertEqual(
            deep_context_tool(
                {"request": [_DerivedRequestContext("derived")]},
                ("marker", 2),
                {"one", "two"},
            ),
            "derived:marker:2",
        )
        with self.assertRaisesRegex(TypeError, "dict\\[str, list") as error_context:
            deep_context_tool(
                {"request": [_AlternateRequestContext()]},
                ("marker", 2),
                {"one"},
            )
        self.assertNotIn("_AlternateRequestContext", str(error_context.exception))

        @tool(
            name="object_context_tool",
            purpose="Validate object Context None compatibility.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The observed object marker.",
            common_failures="The object Context is invalid.",
        )
        def object_context_tool(value: ToolContext[object]) -> str:
            return "none" if value is None else "value"

        with self.assertWarnsRegex(RuntimeWarning, "OptionalToolContext"):
            self.assertEqual(object_context_tool(None), "none")

        with self.assertRaisesRegex(ValueError, "cannot contain unions"):

            @tool(
                name="invalid_nested_union_context",
                purpose="Reject nested Context unions.",
                when_to_use="Use only in tests.",
                parameters=dict(),
                returns="No result is expected.",
                common_failures="Registration must fail.",
            )
            def invalid_nested_union_context(
                payload: ToolContext[list[_RequestContext | _AlternateRequestContext]],
            ) -> str:
                del payload
                return "unexpected"

    def test_tool_context_rejects_empty_fixed_tuple_at_registration(self) -> None:
        """Empty fixed tuple Context annotations must fail before tool execution."""

        body_called = False

        with self.assertRaisesRegex(ValueError, "empty fixed tuple"):

            @tool(
                name="invalid_empty_tuple_context",
                purpose="Reject an unsupported empty fixed tuple Context annotation.",
                when_to_use="Use only in tests.",
                parameters=dict(),
                returns="No result is expected.",
                common_failures="Registration must fail.",
            )
            def invalid_empty_tuple_context(
                payload: ToolContext[tuple[()]],
            ) -> str:
                nonlocal body_called
                body_called = True
                del payload
                return "unexpected"

        self.assertFalse(body_called)

        @tool(
            name="bare_tuple_context",
            purpose="Verify bare tuple Context compatibility.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The tuple length.",
            common_failures="The Context payload is invalid.",
        )
        def bare_tuple_context(payload: ToolContext[tuple]) -> str:
            return str(len(payload))

        @tool(
            name="fixed_tuple_context",
            purpose="Verify fixed tuple Context compatibility.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The fixed tuple marker.",
            common_failures="The Context payload is invalid.",
        )
        def fixed_tuple_context(payload: ToolContext[tuple[str, int]]) -> str:
            return f"{payload[0]}:{payload[1]}"

        @tool(
            name="variadic_tuple_context",
            purpose="Verify variadic tuple Context compatibility.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The variadic tuple length.",
            common_failures="The Context payload is invalid.",
        )
        def variadic_tuple_context(payload: ToolContext[tuple[str, ...]]) -> str:
            return str(len(payload))

        self.assertEqual(bare_tuple_context(("one", 2)), "2")
        self.assertEqual(fixed_tuple_context(("marker", 2)), "marker:2")
        self.assertEqual(variadic_tuple_context(("one", "two")), "2")

    def test_context_defaults_and_mixed_agent_contracts(self) -> None:
        """Context defaults and shared Agent names must follow one contract."""

        default_context = _RequestContext("source-default")
        observed_request_ids: list[str] = []

        @tool(
            name="echo_tool",
            purpose="Use a required Context with a source default.",
            when_to_use="Use only in tests.",
            parameters={"text": "Text to return."},
            returns="The text and resolved Context identifier.",
            common_failures="The Context must be valid.",
        )
        def required_default_context_tool(
            text: str,
            request: ToolContext[_RequestContext] = default_context,
        ) -> str:
            observed_request_ids.append(request.request_id)
            return f"{text}:{request.request_id}"

        @tool(
            name="optional_default_context_tool",
            purpose="Use an optional Context with a source default.",
            when_to_use="Use only in tests.",
            parameters=dict(),
            returns="The resolved Context identifier.",
            common_failures="The Context must be valid.",
        )
        def optional_default_context_tool(
            request: OptionalToolContext[_RequestContext] = default_context,
        ) -> str:
            return request.request_id

        @tool(
            name="optional_after_text_context_tool",
            purpose="Use an optional Context after an ordinary argument.",
            when_to_use="Use only in tests.",
            parameters={"text": "Text to return."},
            returns="The text and optional Context marker.",
            common_failures="The tool should not fail.",
        )
        def optional_after_text_context_tool(
            text: str,
            request: OptionalToolContext[_RequestContext],
        ) -> str:
            return f"{text}:{'none' if request is None else request.request_id}"

        self.assertEqual(
            required_default_context_tool("direct"),
            "direct:source-default",
        )
        self.assertEqual(optional_default_context_tool(), "source-default")
        self.assertEqual(optional_after_text_context_tool("optional"), "optional:none")
        self.assertIsNone(
            inspect.signature(optional_after_text_context_tool)
            .parameters["request"]
            .default
        )

        observed_request_ids.clear()
        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                tools=[
                    required_default_context_tool,
                    optional_default_context_tool,
                ],
                enable_fileglide=False,
            )
            result = agent.run("use_tool")

        self.assertEqual(result, "tool-result:done")
        self.assertEqual(observed_request_ids, ["source-default"])

    def test_model_config_defaults_and_base_url_override(self) -> None:
        """ModelConfig defaults and explicit base_url overrides must work."""

        default_model = build_runtime_model(
            ModelConfig(model="openai/gpt-4.1-mini", api_key="k"),
        )
        override_model = build_runtime_model(
            ModelConfig(
                model="openai/gpt-4.1-mini",
                api_key="k",
                base_url="https://api.deepseek.com/v1",
            )
        )

        self.assertEqual(
            default_model.client_args["base_url"], "https://api.openai.com/v1"
        )
        self.assertEqual(
            override_model.client_args["base_url"], "https://api.deepseek.com/v1"
        )
        self.assertEqual(default_model.client_args["custom_llm_provider"], "openai")
        self.assertEqual(override_model.client_args["custom_llm_provider"], "openai")
        self.assertEqual(default_model.get_config()["params"]["temperature"], 0.01)
        self.assertEqual(default_model.get_config()["params"]["top_p"], 0.01)

    def test_deepseek_runtime_model_preserves_reasoning_for_tool_calls(self) -> None:
        """DeepSeek tool-call history must preserve reasoning."""

        deepseek_model = build_runtime_model(
            ModelConfig(
                model="deepseek-v4-pro",
                api_key="k",
                base_url="https://api.deepseek.com/v1",
            )
        )
        fallback_model = build_runtime_model(
            ModelConfig(
                model="openai/gpt-4.1-mini",
                api_key="k",
                base_url="https://api.deepseek.com/v1",
            )
        )
        messages: Messages = [
            {
                "role": "assistant",
                "content": [
                    {"reasoningContent": {"reasoningText": {"text": "先调用工具"}}},
                    {
                        "toolUse": {
                            "toolUseId": "tool-1",
                            "name": "echo_tool",
                            "input": {"text": "pong"},
                        }
                    },
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": "tool-1",
                            "status": "success",
                            "content": [{"text": "done"}],
                        }
                    }
                ],
            },
            {"role": "user", "content": [{"text": "继续"}]},
        ]

        deepseek_messages = deepseek_model.format_request_messages(messages)

        self.assertIsInstance(deepseek_model, LiteLLMModel)
        self.assertIs(type(fallback_model), LiteLLMModel)
        self.assertEqual(deepseek_messages[0]["reasoning_content"], "先调用工具")
        self.assertEqual(deepseek_messages[0]["content"], "")
        self.assertEqual(
            deepseek_messages[0]["tool_calls"][0]["function"]["name"],
            "echo_tool",
        )
        self.assertEqual(deepseek_messages[1]["role"], "tool")

    def test_tool_contract_validation_and_tooloutput_events(self) -> None:
        """Tool contracts must preserve ToolOutput preview and detail."""

        with self.assertRaisesRegex(ValueError, "Missing parameter docs"):

            @tool(
                name="bad_tool",
                purpose="测试",
                when_to_use="测试",
                parameters={"other": "错误参数"},
                returns="测试",
                common_failures=["失败"],
            )
            def _bad_tool(text: str) -> str:
                return text

        @tool(
            name="ping_tool",
            purpose="返回固定文本。",
            when_to_use="当模型需要一个无需输入的探活工具时使用。",
            parameters=dict(),
            returns="返回固定文本 pong。",
            common_failures=["不会失败"],
        )
        def ping_tool() -> str:
            return "pong"

        with self.assertRaisesRegex(ValueError, "Missing parameter docs"):

            @tool(
                name="still_bad_tool",
                purpose="测试",
                when_to_use="测试",
                parameters=dict(),
                returns="测试",
                common_failures=["失败"],
            )
            def _still_bad_tool(text: str) -> str:
                return text

        @tool(
            name="echo_tool",
            purpose="返回固定 ToolOutput。",
            when_to_use="当模型需要演示工具事件时使用。",
            parameters={"text": "要原样返回的文本。"},
            returns="返回 data/model_text/preview/detail。",
            common_failures=["不会失败"],
        )
        def echo_tool(text: str) -> ToolOutput:
            return ToolOutput(
                data={"text": text},
                model_text=f"model:{text}",
                preview=f"preview:{text}",
                detail=f"detail:{text}",
            )

        self.assertEqual(ping_tool(), "pong")

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                tools=[echo_tool],
            )
            events = list(agent.stream("use_tool"))

        completed_tool_events = [
            event
            for event in events
            if event.kind == "tool" and event.status == "completed"
        ]
        self.assertEqual(len(completed_tool_events), 1)
        tool_event = completed_tool_events[0]
        self.assertEqual(tool_event.name, "echo_tool")
        self.assertEqual(tool_event.data["output"]["preview"], "preview:pong")
        self.assertEqual(tool_event.data["output"]["detail"], "detail:pong")

    def test_agent_session_reuse_and_reset(self) -> None:
        """An Agent must reuse its session and start a new one after reset."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            first = agent.run("first")
            second = agent.run("second")
            agent.reset()
            third = agent.run("third")

        self.assertEqual(first, "turn:1 first")
        self.assertEqual(second, "turn:2 second")
        self.assertEqual(third, "turn:1 third")

    def test_agent_cancel_is_noop_while_idle(self) -> None:
        """Calling cancel while idle must not affect a later invocation."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            agent.cancel()
            result = agent.run("after-idle-cancel")

        self.assertEqual(result, "turn:1 after-idle-cancel")

    def test_agent_rejects_reentry_and_releases_after_cancellation(self) -> None:
        """A busy Agent must reject reentry and later become reusable."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            self.assertIs(easyharness.AgentBusyError, AgentBusyError)

            lazy_stream = agent.stream("slow_stream")
            self.assertIn(
                "before-stream-consumption", agent.run("before-stream-consumption")
            )
            self.assertIsNotNone(next(lazy_stream))

            with self.assertRaises(AgentBusyError):
                agent.run("reentrant-run")
            with self.assertRaises(AgentBusyError):
                agent.reset()

            agent.cancel()
            list(lazy_stream)
            self.assertIn("after-stream-cancel", agent.run("after-stream-cancel"))

            with self.assertRaisesRegex(ValueError, "Unknown tool Context parameters"):
                agent.run("invalid-context", unknown=object())
            self.assertIn("after-invalid-context", agent.run("after-invalid-context"))

    def test_cancel_targets_agent_active_when_request_started(self) -> None:
        """取消请求必须作用于开始时的活动会话，而非随后重置的新会话。"""

        class StubAgent:
            """记录取消调用的最小底层 Agent 替身。"""

            def __init__(self) -> None:
                """初始化尚未收到取消信号的替身。"""

                self.cancelled = False

            def cancel(self) -> None:
                """记录一次取消请求。"""

                self.cancelled = True

        class InterleavingLock:
            """在 cancel 释放锁时模拟旧调用结束及随后完成的会话重置。"""

            def __init__(self, runtime: _StrandsRuntime, next_agent: StubAgent) -> None:
                """保存需要在临界区结束后切换的运行时和新会话。"""

                self.runtime = runtime
                self.next_agent = next_agent
                self.interleaved = False

            def __enter__(self) -> InterleavingLock:
                """提供 Lock 所需的上下文管理器入口。"""

                return self

            def __exit__(
                self,
                exception_type: object,
                exception: object,
                traceback: object,
            ) -> None:
                """在首次释放时切换到已重置的新会话。"""

                del exception_type, exception, traceback
                if not self.interleaved:
                    self.interleaved = True
                    self.runtime._active_invocations = 0
                    self.runtime._agent = self.next_agent

        runtime = object.__new__(_StrandsRuntime)
        runtime._active_invocations = 1
        old_agent = StubAgent()
        new_agent = StubAgent()
        runtime._agent = old_agent
        runtime._state_lock = InterleavingLock(runtime, new_agent)

        runtime.cancel()

        self.assertTrue(old_agent.cancelled)
        self.assertFalse(new_agent.cancelled)

    def test_stream_cancel_emits_cancelled_phase_and_system_events(self) -> None:
        """Stream cancellation must emit assistant and system cancellation events."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            observed = []
            for event in agent.stream("slow_stream"):
                observed.append(event)
                if event.kind == "assistant" and event.status == "delta":
                    agent.cancel()

            resumed = agent.run("after-stream-cancel")

        self.assertIn(
            ("assistant", "cancelled"),
            [(event.kind, event.status) for event in observed],
        )
        self.assertIn(
            ("system", "cancelled"),
            [(event.kind, event.status) for event in observed],
        )
        final_system = next(
            event
            for event in reversed(observed)
            if event.kind == "system" and event.status == "cancelled"
        )
        self.assertEqual(final_system.data["stop_reason"], "cancelled")
        self.assertIn("after-stream-cancel", resumed)

    def test_stream_cancel_before_first_delta_still_emits_system_cancelled(
        self,
    ) -> None:
        """Cancelling before a first delta must emit a final system event."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            observed: list = []

            def consume() -> None:
                observed.extend(agent.stream("slow_start"))

            worker = threading.Thread(target=consume)
            worker.start()
            time.sleep(0.05)
            agent.cancel()
            worker.join(timeout=3)

        self.assertFalse(worker.is_alive())
        self.assertEqual(
            [(event.kind, event.status) for event in observed],
            [("system", "cancelled")],
        )

    def test_run_cancel_returns_cancelled_text_and_agent_stays_usable(self) -> None:
        """Cancelling a run must leave the Agent reusable."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            result_holder: dict[str, str] = dict()

            def invoke() -> None:
                result_holder["value"] = agent.run("slow_stream")

            worker = threading.Thread(target=invoke)
            worker.start()
            time.sleep(0.05)
            agent.cancel()
            worker.join(timeout=3)
            resumed = agent.run("after-run-cancel")

        self.assertFalse(worker.is_alive())
        self.assertEqual(result_holder["value"], "Cancelled by user")
        self.assertIn("after-run-cancel", resumed)

    def test_event_mapper_marks_tool_phase_cancelled_when_result_is_cancelled(
        self,
    ) -> None:
        """The mapper must normalize cancelled tool and system events."""

        output_queue: queue.Queue[object] = queue.Queue()
        mapper = _EventMapper(output_queue)
        mapper.feed(
            {
                "type": "tool_stream",
                "tool_stream_event": {
                    "data": {
                        "easyharness_tool": {
                            "status": "started",
                            "name": "echo_tool",
                            "tool_use_id": "tool-1",
                            "started_at": utc_now_iso(),
                            "input": {"text": "pong"},
                        }
                    }
                },
            }
        )
        mapper.feed(
            {
                "result": SimpleNamespace(
                    stop_reason="cancelled",
                    message={
                        "role": "assistant",
                        "content": [{"text": "Cancelled by user"}],
                    },
                )
            }
        )

        observed = []
        while not output_queue.empty():
            observed.append(output_queue.get())

        self.assertEqual(
            [(event.kind, event.status) for event in observed],
            [
                ("tool", "started"),
                ("tool", "cancelled"),
                ("system", "cancelled"),
            ],
        )

    def test_event_mapper_keeps_same_name_tool_events_correlated(self) -> None:
        """Same-name tool events must retain their original tool-use ID."""

        output_queue: queue.Queue[object] = queue.Queue()
        mapper = _EventMapper(output_queue)
        started_at = utc_now_iso()

        def feed_tool_event(
            *,
            status: str,
            tool_use_id: str,
            name: str = "echo_tool",
            output: dict[str, object] | None = None,
        ) -> None:
            payload: dict[str, object] = {
                "status": status,
                "name": name,
                "tool_use_id": tool_use_id,
                "started_at": started_at,
                "input": {"text": tool_use_id},
            }
            if output is not None:
                payload["output"] = output
            mapper.feed(
                {
                    "type": "tool_stream",
                    "tool_stream_event": {"data": {"easyharness_tool": payload}},
                }
            )

        feed_tool_event(status="started", tool_use_id="tool-1")
        feed_tool_event(status="started", tool_use_id="tool-2")
        feed_tool_event(
            status="completed",
            tool_use_id="tool-1",
            output={"preview": "done-1"},
        )
        feed_tool_event(
            status="completed",
            tool_use_id="tool-2",
            output={"preview": "done-2"},
        )

        observed = []
        while not output_queue.empty():
            observed.append(output_queue.get())

        self.assertEqual(
            [event.data["tool_use_id"] for event in observed],
            ["tool-1", "tool-2", "tool-1", "tool-2"],
        )
        self.assertEqual(
            [event.text for event in observed if event.status == "completed"],
            ["done-1", "done-2"],
        )

    def test_event_mapper_keeps_different_tool_events_correlated(self) -> None:
        """Different tool events must retain distinct identity fields."""

        output_queue: queue.Queue[object] = queue.Queue()
        mapper = _EventMapper(output_queue)
        started_at = utc_now_iso()

        def feed_tool_event(
            *,
            status: str,
            tool_use_id: str,
            name: str,
            output: dict[str, object] | None = None,
        ) -> None:
            payload: dict[str, object] = {
                "status": status,
                "name": name,
                "tool_use_id": tool_use_id,
                "started_at": started_at,
                "input": {"name": name},
            }
            if output is not None:
                payload["output"] = output
            mapper.feed(
                {
                    "type": "tool_stream",
                    "tool_stream_event": {"data": {"easyharness_tool": payload}},
                }
            )

        feed_tool_event(status="started", tool_use_id="tool-1", name="tool_alpha")
        feed_tool_event(status="started", tool_use_id="tool-2", name="tool_beta")
        feed_tool_event(
            status="completed",
            tool_use_id="tool-1",
            name="tool_alpha",
            output={"preview": "alpha-done"},
        )

        observed = []
        while not output_queue.empty():
            observed.append(output_queue.get())

        completed_event = observed[-1]
        self.assertEqual(completed_event.name, "tool_alpha")
        self.assertEqual(completed_event.data["tool_use_id"], "tool-1")
        self.assertEqual(completed_event.data["input"], {"name": "tool_alpha"})
        self.assertEqual(
            completed_event.data["output"]["preview"],
            "alpha-done",
        )

    def test_event_mapper_cancels_each_active_tool_phase(self) -> None:
        """Cancellation must finish every active tool phase."""

        output_queue: queue.Queue[object] = queue.Queue()
        mapper = _EventMapper(output_queue)
        started_at = utc_now_iso()

        for tool_use_id in ("tool-1", "tool-2"):
            mapper.feed(
                {
                    "type": "tool_stream",
                    "tool_stream_event": {
                        "data": {
                            "easyharness_tool": {
                                "status": "started",
                                "name": "echo_tool",
                                "tool_use_id": tool_use_id,
                                "started_at": started_at,
                                "input": {"text": tool_use_id},
                            }
                        }
                    },
                }
            )

        mapper.feed(
            {
                "result": SimpleNamespace(
                    stop_reason="cancelled",
                    message={
                        "role": "assistant",
                        "content": [{"text": "Cancelled by user"}],
                    },
                )
            }
        )

        observed = []
        while not output_queue.empty():
            observed.append(output_queue.get())

        cancelled_tool_ids = [
            event.data["tool_use_id"]
            for event in observed
            if event.kind == "tool" and event.status == "cancelled"
        ]
        self.assertEqual(cancelled_tool_ids, ["tool-1", "tool-2"])
        self.assertEqual(
            (observed[-1].kind, observed[-1].status), ("system", "cancelled")
        )

    def test_default_eventing_manager_owns_compression_defaults(self) -> None:
        """The default summary manager must own compression defaults."""

        manager = EventingSummarizingConversationManager()

        self.assertEqual(manager.summary_ratio, 0.3)
        self.assertEqual(manager.preserve_recent_messages, 8)
        self.assertEqual(manager._compression_threshold, 0.7)

    def test_default_compress_events_use_proactive_mode(self) -> None:
        """Default compression must emit a proactive compression event."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(overflow_threshold=12),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            for index in range(5):
                agent.run(f"warmup-{index}")
            manager = agent._runtime._conversation_manager
            raw_events: list[dict[str, object]] = []
            manager.bind_event_sink(raw_events.append)
            manager._on_before_model_call_threshold(
                SimpleNamespace(
                    agent=agent._runtime._agent,
                    projected_input_tokens=90,
                )
            )
            manager.bind_event_sink(None)

        compress_events = [event["easyharness_compress"] for event in raw_events]
        compress_statuses = [event["status"] for event in compress_events]
        compress_modes = [event["mode"] for event in compress_events]
        self.assertIn("started", compress_statuses)
        self.assertIn("completed", compress_statuses)
        self.assertIn("proactive", compress_modes)

    def test_reactive_compress_failure_still_raises_when_proactive_disabled(
        self,
    ) -> None:
        """Reactive summary failure must raise without proactive compression."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(overflow_threshold=12, fail_summary=True),
        ):
            failed_agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                conversation_manager=EventingSummarizingConversationManager(
                    proactive_compression=None,
                ),
            )
            for index in range(6):
                failed_agent.run(f"warmup-{index}")

            observed = []
            with self.assertRaisesRegex(RuntimeError, "summary failed"):
                for event in failed_agent.stream("trigger-overflow"):
                    observed.append(event)

        failed_compress_events = [
            event
            for event in observed
            if event.kind == "compress" and event.status == "failed"
        ]
        self.assertTrue(failed_compress_events)
        self.assertIn(
            "reactive",
            [event.data["mode"] for event in failed_compress_events],
        )

    def test_custom_conversation_manager_override(self) -> None:
        """A supplied custom manager must retain its custom compression behavior."""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(overflow_threshold=2),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                conversation_manager=CustomConversationManager(),
            )
            agent.run("warmup")
            events = list(agent.stream("trigger-custom"))

        compress_modes = [
            event.data["mode"] for event in events if event.kind == "compress"
        ]
        self.assertIn("custom", compress_modes)

    def test_eventing_manager_allows_explicit_override_values(self) -> None:
        """Callers must be able to override default proactive and retention settings."""

        manager = EventingSummarizingConversationManager(
            summary_ratio=0.5,
            preserve_recent_messages=12,
            proactive_compression=None,
        )

        self.assertEqual(manager.summary_ratio, 0.5)
        self.assertEqual(manager.preserve_recent_messages, 12)
        self.assertIsNone(manager._compression_threshold)

    def test_toolset_builder_keeps_root_public_surface_minimal(self) -> None:
        """Importing the toolset builder must not expand the root SDK public surface."""

        from easyharness.toolset import build_fileglide_tools

        self.assertTrue(callable(build_fileglide_tools))
        self.assertEqual(
            set(easyharness.__all__),
            {
                "Agent",
                "AgentBusyError",
                "ModelConfig",
                "AgentEvent",
                "ToolContext",
                "OptionalToolContext",
                "ToolOutput",
                "tool",
            },
        )

    def test_fileglide_toolset_contains_expected_tools_and_respects_root(self) -> None:
        """Official FileGlide tools must honor their root scope."""

        from easyharness.toolset import build_fileglide_tools

        with (
            tempfile.TemporaryDirectory() as root_dir,
            tempfile.TemporaryDirectory() as outside_dir,
        ):
            root_path = Path(root_dir)
            outside_path = Path(outside_dir)
            (root_path / "demo.txt").write_text("alpha\nbeta\n", encoding="utf-8")
            (outside_path / "secret.txt").write_text("secret\n", encoding="utf-8")

            tools = build_fileglide_tools(default_root=root_path)
            tool_map = {item.tool_name: item for item in tools}

            self.assertEqual(
                set(tool_map),
                {
                    "fileglide_list_tree",
                    "fileglide_search_paths",
                    "fileglide_read_text",
                    "fileglide_search_text",
                    "fileglide_edit_text",
                    "fileglide_manage_paths",
                    "fileglide_inspect_path",
                },
            )
            for tool_name, tool_obj in tool_map.items():
                properties = tool_obj.tool_spec["inputSchema"]["json"]["properties"]
                self.assertIn("root", properties, tool_name)
                root_description = properties["root"]["description"]
                self.assertIn('MUST NOT use ".." path segments', root_description)
                self.assertIn(
                    "MUST use an explicit `root` argument",
                    root_description,
                )
                self.assertIn(
                    "MUST remain a normalized EasyHarness result payload.",
                    tool_obj.tool_spec["description"],
                )

            read_output = tool_map["fileglide_read_text"]("demo.txt")
            self.assertTrue(read_output.data["ok"])
            self.assertEqual(read_output.data["root"], str(root_path.resolve()))
            self.assertEqual(
                read_output.data["result"]["content"].splitlines(),
                ["alpha", "beta"],
            )

            escaped_output = tool_map["fileglide_read_text"](
                str(outside_path / "secret.txt")
            )
            self.assertFalse(escaped_output.data["ok"])
            self.assertEqual(escaped_output.data["error"]["code"], "scope_violation")

    def test_fileglide_toolset_allows_explicit_root_override(self) -> None:
        """Official FileGlide tools must allow an explicit call-time root override."""

        from easyharness.toolset import build_fileglide_tools

        with (
            tempfile.TemporaryDirectory() as root_dir,
            tempfile.TemporaryDirectory() as outside_dir,
        ):
            root_path = Path(root_dir)
            outside_path = Path(outside_dir)
            parent_path = root_path.parent
            (root_path / "demo.txt").write_text("alpha\nbeta\n", encoding="utf-8")
            (outside_path / "secret.txt").write_text("secret\n", encoding="utf-8")

            tools = build_fileglide_tools(default_root=root_path)
            tool_map = {item.tool_name: item for item in tools}

            sibling_output = tool_map["fileglide_read_text"](
                target=f"{outside_path.name}/secret.txt",
                root=str(parent_path),
            )
            self.assertTrue(sibling_output.data["ok"])
            self.assertEqual(sibling_output.data["root"], str(parent_path.resolve()))
            self.assertEqual(
                sibling_output.data["result"]["content"].splitlines(),
                ["secret"],
            )

            scoped_failure = tool_map["fileglide_read_text"](
                target=f"../{root_path.name}/demo.txt",
                root=str(outside_path),
            )
            self.assertFalse(scoped_failure.data["ok"])
            self.assertEqual(scoped_failure.data["root"], str(outside_path.resolve()))
            self.assertEqual(
                scoped_failure.data["error"]["code"],
                "scope_violation",
            )

    def test_fileglide_toolset_normalizes_preview_payloads_as_json(self) -> None:
        """FileGlide preview payloads must be JSON serializable."""

        from easyharness.toolset import build_fileglide_tools

        with tempfile.TemporaryDirectory() as root_dir:
            root_path = Path(root_dir)
            (root_path / "preview.txt").write_text("preview\n", encoding="utf-8")

            tools = build_fileglide_tools(default_root=root_path)
            tool_map = {item.tool_name: item for item in tools}
            preview_output = tool_map["fileglide_manage_paths"](
                action="delete",
                kind="file",
                target="preview.txt",
                dry_run=True,
            )

            self.assertTrue(preview_output.data["ok"])
            self.assertIsInstance(preview_output.data["result"]["preview"], dict)
            json.dumps(preview_output.data, ensure_ascii=False)

    def test_agent_loads_default_file_tools_and_allows_override(self) -> None:
        """An Agent must support default file tools and caller overrides."""

        @tool(
            name="fileglide_read_text",
            purpose="覆盖默认读文件工具。",
            when_to_use="当测试需要验证同名工具覆盖时使用。",
            parameters={"target": "仅用于测试的目标路径。"},
            returns="返回固定文本。",
            common_failures=["不会失败"],
        )
        def custom_read_text(target: str) -> str:
            del target
            return "custom"

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            default_agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            disabled_agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                enable_fileglide=False,
            )
            overridden_agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
                tools=[custom_read_text],
            )

        default_tool_map = {
            item.tool_name: item for item in default_agent._runtime._tools
        }
        disabled_tool_names = [
            item.tool_name for item in disabled_agent._runtime._tools
        ]
        overridden_tool_map = {
            item.tool_name: item for item in overridden_agent._runtime._tools
        }

        self.assertIn("fileglide_read_text", default_tool_map)
        self.assertEqual(disabled_tool_names, [])
        self.assertIs(
            overridden_tool_map["fileglide_read_text"],
            custom_read_text,
        )
        self.assertIn("fileglide_manage_paths", overridden_tool_map)


if __name__ == "__main__":
    unittest.main()
