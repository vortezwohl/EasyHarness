"""EasyHarness SDK 的最小回归验证。

这些测试优先覆盖公开表面、严格工具合同、多轮会话、事件流和压缩事件，
避免普通调用路径回退到内部 registry、bridge 或私有合同对象。
"""

from __future__ import annotations

import asyncio
import unittest
from collections.abc import AsyncGenerator
import json
from pathlib import Path
import queue
import threading
import time
from types import SimpleNamespace
import tempfile
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
from easyharness import Agent, ModelConfig, ToolOutput, tool
from easyharness._internal.conversation import (
    EventingSummarizingConversationManager,
    InternalEventSink,
    utc_now_iso,
)
from easyharness._internal.model import build_runtime_model
from easyharness._internal.runtime import _EventMapper


def _text_chunk(text: str) -> dict:
    """构造最小文本流事件序列。"""

    return {"contentBlockDelta": {"delta": {"text": text}}}


class _AgentWithMessages(Protocol):
    """声明测试中需要的最小 agent 消息接口。"""

    messages: Messages


class FakeModel(Model):
    """用于 SDK 测试的最小假模型。"""

    def __init__(
        self, *, overflow_threshold: int | None = None, fail_summary: bool = False
    ) -> None:
        """初始化测试模型。

        Args:
            overflow_threshold: 超过该消息条数时触发上下文溢出。
            fail_summary: 是否让摘要调用直接失败。
        """

        self._config = {"context_window_limit": 128}
        self._overflow_threshold = overflow_threshold
        self._fail_summary = fail_summary

    def update_config(self, **model_config: object) -> None:
        """更新测试配置。"""

        self._config.update(model_config)

    def get_config(self) -> dict[str, object]:
        """返回测试配置。"""

        return self._config

    @property
    def context_window_limit(self) -> int:
        """返回测试模型的上下文窗口上限。"""

        return int(self._config["context_window_limit"])

    async def structured_output(
        self,
        output_model: type[BaseModel],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[dict[str, object], None]:
        """测试模型不提供结构化输出。"""

        del output_model, prompt, system_prompt, kwargs
        raise NotImplementedError

    async def count_tokens(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
    ) -> int:
        """用消息数估算 token 数。"""

        del tool_specs, system_prompt, system_prompt_content
        return len(messages) * 10

    @staticmethod
    def _latest_user_text(messages: Messages) -> str:
        """提取最后一条用户文本。"""

        for message in reversed(messages):
            if message["role"] != "user":
                continue
            for block in message["content"]:
                if "text" in block:
                    return block["text"]
        return ""

    @staticmethod
    def _has_tool_result(messages: Messages) -> bool:
        """判断当前消息里是否已经包含工具结果。"""

        return any(
            any("toolResult" in block for block in message["content"])
            for message in messages
        )

    @staticmethod
    def _has_summary_message(messages: Messages) -> bool:
        """判断消息历史里是否已经存在摘要消息。"""

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
        """发出一条普通 assistant 文本响应。"""

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield _text_chunk(text)
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 1,
                    "outputTokens": 1,
                    "totalTokens": 2,
                },
                "metrics": {},
            }
        }

    @staticmethod
    async def _emit_slow_text_response(
        *chunks: str,
        delay_before_first: float = 0.0,
        delay_between: float = 0.0,
    ) -> AsyncGenerator[StreamEvent, None]:
        """按给定节奏发出 assistant 文本响应，便于测试取消路径。"""

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        if delay_before_first > 0:
            await asyncio.sleep(delay_before_first)
        for index, chunk in enumerate(chunks):
            yield _text_chunk(chunk)
            if delay_between > 0 and index < len(chunks) - 1:
                await asyncio.sleep(delay_between)
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 1,
                    "outputTokens": 1,
                    "totalTokens": 2,
                },
                "metrics": {},
            }
        }

    @staticmethod
    async def _emit_tool_request() -> AsyncGenerator[StreamEvent, None]:
        """发出一条带 reasoning 和 toolUse 的响应。"""

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {
            "contentBlockDelta": {
                "delta": {"reasoningContent": {"text": "先调用工具"}},
            }
        }
        yield {"contentBlockStop": {}}
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
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 1,
                    "outputTokens": 1,
                    "totalTokens": 2,
                },
                "metrics": {},
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
        """根据输入消息流式返回最小事件序列。"""

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
    """用于验证自定义 manager 透传的最小实现。"""

    def __init__(self) -> None:
        """初始化自定义 manager。"""

        super().__init__()
        self._event_sink: InternalEventSink | None = None

    def bind_event_sink(self, sink: InternalEventSink | None) -> None:
        """绑定内部事件 sink。"""

        self._event_sink = sink

    def apply_management(self, agent: object, **kwargs: object) -> None:
        """该测试 manager 不做额外管理。"""

        del agent, kwargs

    def reduce_context(
        self,
        agent: _AgentWithMessages,
        e: Exception | None = None,
        **kwargs: object,
    ) -> None:
        """用自定义方式压缩上下文，并发出 compress 事件。"""

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
    """SDK 回归测试集合。"""

    def test_public_surface_exports_only_five_names(self) -> None:
        """顶层公开表面应只暴露五个主要名字。"""

        self.assertEqual(
            set(easyharness.__all__),
            {"Agent", "ModelConfig", "AgentEvent", "ToolOutput", "tool"},
        )
        for name in easyharness.__all__:
            self.assertTrue(hasattr(easyharness, name))

    def test_model_config_defaults_and_base_url_override(self) -> None:
        """ModelConfig 默认值与显式 base_url 覆盖应生效。"""

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
        """DeepSeek tool-call 历史应保留后续请求所需的 reasoning 内容。"""

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
                    {
                        "reasoningContent": {
                            "reasoningText": {"text": "先调用工具"}
                        }
                    },
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
        """工具合同应严格校验，并保留 ToolOutput 的 preview/detail 语义。"""

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
            parameters={},
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
                parameters={},
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
        """Agent 应复用会话，并在 reset 后开启新会话。"""

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
        """空闲态 cancel 不应污染后续 invocation。"""

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

    def test_stream_cancel_emits_cancelled_phase_and_system_events(self) -> None:
        """取消流式输出时应暴露 assistant.cancelled 和 system.cancelled。"""

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

    def test_stream_cancel_before_first_delta_still_emits_system_cancelled(self) -> None:
        """首个公开 delta 之前取消时也应有最终 system.cancelled。"""

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
        """取消同步 run 时应返回取消文本，随后 Agent 仍可继续使用。"""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            result_holder: dict[str, str] = {}

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
        """mapper 应能把取消结果归一化为 tool.cancelled 与 system.cancelled。"""

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
                    message={"role": "assistant", "content": [{"text": "Cancelled by user"}]},
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
        """同名工具重叠时，终态事件应保持原始 tool_use_id 关联。"""

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
                    "tool_stream_event": {
                        "data": {"easyharness_tool": payload}
                    },
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
        """异名工具重叠时，终态事件不得串用其他工具身份字段。"""

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
                    "tool_stream_event": {
                        "data": {"easyharness_tool": payload}
                    },
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
        """取消时，所有活动工具阶段都应收到各自的 cancelled 终态。"""

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
                    message={"role": "assistant", "content": [{"text": "Cancelled by user"}]},
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
        self.assertEqual((observed[-1].kind, observed[-1].status), ("system", "cancelled"))

    def test_default_eventing_manager_owns_compression_defaults(self) -> None:
        """默认事件化摘要 manager 应声明 SDK 自己的压缩默认值。"""

        manager = EventingSummarizingConversationManager()

        self.assertEqual(manager.summary_ratio, 0.3)
        self.assertEqual(manager.preserve_recent_messages, 8)
        self.assertEqual(manager._compression_threshold, 0.7)

    def test_default_compress_events_use_proactive_mode(self) -> None:
        """默认摘要 manager 应在 proactive 压缩时发出 compress 事件。"""

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

        compress_events = [
            event["easyharness_compress"] for event in raw_events
        ]
        compress_statuses = [event["status"] for event in compress_events]
        compress_modes = [event["mode"] for event in compress_events]
        self.assertIn("started", compress_statuses)
        self.assertIn("completed", compress_statuses)
        self.assertIn("proactive", compress_modes)

    def test_reactive_compress_failure_still_raises_when_proactive_disabled(
        self,
    ) -> None:
        """关闭 proactive 后，reactive 摘要失败仍应继续抛错。"""

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
        """传入自定义 manager 时应复用自定义压缩行为。"""

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
        """调用方应能覆盖默认 proactive 与 retention 配置。"""

        manager = EventingSummarizingConversationManager(
            summary_ratio=0.5,
            preserve_recent_messages=12,
            proactive_compression=None,
        )

        self.assertEqual(manager.summary_ratio, 0.5)
        self.assertEqual(manager.preserve_recent_messages, 12)
        self.assertIsNone(manager._compression_threshold)

    def test_toolset_builder_keeps_root_public_surface_minimal(self) -> None:
        """导入 toolset builder 不应扩张根包公开 SDK 名字集。"""

        from easyharness.toolset import build_fileglide_tools

        self.assertTrue(callable(build_fileglide_tools))
        self.assertEqual(
            set(easyharness.__all__),
            {"Agent", "ModelConfig", "AgentEvent", "ToolOutput", "tool"},
        )

    def test_fileglide_toolset_contains_expected_tools_and_respects_root(self) -> None:
        """官方 fileglide 工具集应包含约定名称，并遵循 root 作用域。"""

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
        """官方 fileglide 工具应支持调用期显式 root 覆盖。"""

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
        """fileglide dataclass 结果应被归一化为 JSON 可序列化结构。"""

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
        """Agent 应默认装载官方文件工具，允许禁用和同名覆盖。"""

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
