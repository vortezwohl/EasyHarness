"""EasyHarness 的会话型 Agent 运行时。

本模块把公开 `Agent` 封装成极简同步接口，内部复用 Strands 运行时、工具执
行器和会话管理器，同时把底层回调事件映射成稳定的 `AgentEvent`。
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator

from strands import Agent as StrandsAgent

from .conversation import bind_event_sink_if_supported, clone_conversation_manager
from .model import build_runtime_model
from .types import AgentEvent, ModelConfig

_STREAM_END = object()


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""

    return datetime.now(timezone.utc).isoformat()


def _extract_message_text(message: dict[str, Any] | None) -> str:
    """从 Strands message 中提取可读文本。"""

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
    """记录一个流式阶段的开始状态与累计文本。"""

    started_at: str
    started_monotonic: float
    chunks: list[str]


class _EventMapper:
    """把底层运行时事件映射成公开 `AgentEvent`。"""

    def __init__(self, output_queue: "queue.Queue[object]") -> None:
        """初始化事件映射器。

        Args:
            output_queue: 发送给同步消费者的事件队列。
        """

        self._output_queue = output_queue
        self._thinking: _PhaseState | None = None
        self._assistant: _PhaseState | None = None

    def _emit(
        self,
        *,
        kind: str,
        status: str,
        text: str | None = None,
        name: str | None = None,
        started_at: str | None = None,
        duration_ms: int | None = None,
        data: Any = None,
    ) -> None:
        """放入一个公开事件。"""

        self._output_queue.put(
            AgentEvent(
                kind=kind,  # type: ignore[arg-type]
                status=status,  # type: ignore[arg-type]
                text=text,
                name=name,
                started_at=started_at,
                duration_ms=duration_ms,
                data=data,
            )
        )

    def _start_phase(self, phase: str) -> _PhaseState:
        """创建新的阶段状态。"""

        return _PhaseState(started_at=utc_now_iso(), started_monotonic=time.perf_counter(), chunks=[])

    def _flush_thinking(self, status: str = "completed", text_override: str | None = None) -> None:
        """结束 thinking 阶段并发出完成事件。"""

        if self._thinking is None:
            return

        text = text_override if text_override is not None else "".join(self._thinking.chunks)
        duration_ms = int((time.perf_counter() - self._thinking.started_monotonic) * 1000)
        self._emit(
            kind="thinking",
            status=status,
            text=text or None,
            started_at=self._thinking.started_at,
            duration_ms=duration_ms,
        )
        self._thinking = None

    def _flush_assistant(self, status: str = "completed", text_override: str | None = None) -> None:
        """结束 assistant 阶段并发出完成事件。"""

        if self._assistant is None:
            return

        text = text_override if text_override is not None else "".join(self._assistant.chunks)
        duration_ms = int((time.perf_counter() - self._assistant.started_monotonic) * 1000)
        self._emit(
            kind="assistant",
            status=status,
            text=text or None,
            started_at=self._assistant.started_at,
            duration_ms=duration_ms,
        )
        self._assistant = None

    def emit_internal(self, payload: dict[str, Any]) -> None:
        """处理 conversation manager 直接推送的内部事件。"""

        compress_event = payload.get("easyharness_compress")
        if not compress_event:
            return

        self._emit(
            kind="compress",
            status=compress_event["status"],
            started_at=compress_event.get("started_at"),
            duration_ms=compress_event.get("duration_ms"),
            text=compress_event.get("error"),
            data={"mode": compress_event.get("mode")},
        )

    def feed(self, raw_event: dict[str, Any]) -> None:
        """消费一条底层事件。

        Args:
            raw_event: Strands `stream_async` 产出的原始事件字典。
        """

        if "reasoningText" in raw_event:
            if self._thinking is None:
                self._flush_assistant()
                self._thinking = self._start_phase("thinking")
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
                self._assistant = self._start_phase("assistant")
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
                self._assistant = self._start_phase("assistant")
            self._flush_thinking()
            self._flush_assistant(text_override=final_text or None)
            return

        if raw_event.get("event_loop_throttled_delay") is not None:
            self._emit(
                kind="system",
                status="delta",
                text=f"tool/model throttled: {raw_event['event_loop_throttled_delay']}s",
                started_at=utc_now_iso(),
            )

    def finalize(self) -> None:
        """在流结束时刷新残留阶段。"""

        self._flush_thinking()
        self._flush_assistant()

    def fail(self, error: BaseException) -> None:
        """在流异常结束时发出失败事件。"""

        self._flush_thinking(status="failed", text_override=str(error))
        self._flush_assistant(status="failed", text_override=str(error))
        self._emit(
            kind="system",
            status="failed",
            text=str(error),
            started_at=utc_now_iso(),
        )


class _StrandsRuntime:
    """EasyHarness 对 Strands Runtime 的极简桥接层。"""

    def __init__(
        self,
        *,
        model_config: ModelConfig,
        system_prompt: str,
        tools: Iterable[Any],
        conversation_manager: Any | None,
    ) -> None:
        """初始化内部运行时。

        Args:
            model_config: 公开模型配置。
            system_prompt: 系统提示词。
            tools: 公开工具列表。
            conversation_manager: 调用方可选传入的自定义 manager。
        """

        self._model_config = model_config
        self._system_prompt = system_prompt
        self._tools = list(tools)
        self._conversation_manager_template = conversation_manager
        self._agent: StrandsAgent
        self._conversation_manager: Any
        self.reset()

    def _create_agent(self) -> StrandsAgent:
        """构造新的底层 Strands Agent。"""

        self._conversation_manager = clone_conversation_manager(self._conversation_manager_template)
        return StrandsAgent(
            model=build_runtime_model(self._model_config),
            system_prompt=self._system_prompt,
            tools=self._tools,
            conversation_manager=self._conversation_manager,
            callback_handler=None,
        )

    def reset(self) -> None:
        """重建底层 agent，清空会话状态。"""

        self._agent = self._create_agent()

    def run(self, prompt: str) -> str:
        """执行一次同步会话调用并返回最终文本。

        Args:
            prompt: 当前轮用户输入。

        Returns:
            当前轮 assistant 的最终文本。
        """

        bind_event_sink_if_supported(self._conversation_manager, None)
        result = self._agent(prompt)
        return str(result).strip()

    def stream(self, prompt: str) -> Iterator[AgentEvent]:
        """以同步生成器形式返回公开事件流。

        Args:
            prompt: 当前轮用户输入。

        Yields:
            统一的 `AgentEvent` 对象。
        """

        output_queue: "queue.Queue[object]" = queue.Queue()

        def worker() -> None:
            mapper = _EventMapper(output_queue)

            async def runner() -> None:
                bind_event_sink_if_supported(self._conversation_manager, mapper.emit_internal)
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
    """EasyHarness 面向调用方的唯一主入口。

    Args:
        model: 公开模型配置。
        system_prompt: 当前会话使用的系统提示词。
        tools: 当前 agent 可调用的工具列表。
        conversation_manager: 可选自定义会话管理器；未提供时使用默认摘要型 manager。
    """

    def __init__(
        self,
        model: ModelConfig,
        system_prompt: str,
        tools: list[Any] | None = None,
        conversation_manager: Any | None = None,
    ) -> None:
        """初始化一个会话型 Agent。"""

        self._runtime = _StrandsRuntime(
            model_config=model,
            system_prompt=system_prompt,
            tools=tools or [],
            conversation_manager=conversation_manager,
        )

    def run(self, prompt: str) -> str:
        """执行一轮会话并返回最终文本结果。

        Args:
            prompt: 当前轮用户输入。

        Returns:
            assistant 的最终文本输出。
        """

        return self._runtime.run(prompt)

    def stream(self, prompt: str) -> Iterator[AgentEvent]:
        """执行一轮会话并返回统一事件流。

        Args:
            prompt: 当前轮用户输入。

        Yields:
            统一的 `AgentEvent`。
        """

        yield from self._runtime.stream(prompt)

    def reset(self) -> None:
        """清空当前会话状态并开始新会话。"""

        self._runtime.reset()
