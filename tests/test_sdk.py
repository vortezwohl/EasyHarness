"""EasyHarness SDK 的最小回归验证。

这些测试优先覆盖公开表面、严格工具合同、多轮会话、事件流和压缩事件，
避免普通调用路径回退到内部 registry、bridge 或私有合同对象。
"""

from __future__ import annotations

import unittest
from collections.abc import AsyncGenerator
import json
from pathlib import Path
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
from easyharness._internal.conversation import InternalEventSink, utc_now_iso
from easyharness._internal.model import build_runtime_model


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

    def test_default_compress_events_and_failure_semantics(self) -> None:
        """默认摘要 manager 应发出 compress 事件，并在 reactive 失败时继续抛错。"""

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(overflow_threshold=12),
        ):
            agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            for index in range(6):
                agent.run(f"warmup-{index}")
            events = list(agent.stream("trigger-overflow"))

        compress_statuses = [
            event.status for event in events if event.kind == "compress"
        ]
        self.assertIn("started", compress_statuses)
        self.assertIn("completed", compress_statuses)

        with mock.patch(
            "easyharness._internal.runtime.build_runtime_model",
            return_value=FakeModel(overflow_threshold=12, fail_summary=True),
        ):
            failed_agent = Agent(
                model=ModelConfig(model="fake", api_key="fake"),
                system_prompt="test",
            )
            for index in range(6):
                failed_agent.run(f"warmup-{index}")

            observed = []
            with self.assertRaisesRegex(RuntimeError, "summary failed"):
                for event in failed_agent.stream("trigger-overflow"):
                    observed.append(event)

        self.assertIn(
            "failed",
            [event.status for event in observed if event.kind == "compress"],
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
