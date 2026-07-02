"""EasyHarness 的严格工具合同实现。

本模块提供公开 `tool` 装饰器，并把函数签名、类型注解、参数文档和运行时
返回值收敛成一个内部 `AgentTool`。普通开发者只需要写 Python 函数和完整元
数据，不需要接触 Strands 的原生工具装饰器或私有合同对象。
"""

from __future__ import annotations

import inspect
import json
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Sequence, get_type_hints

from pydantic import Field, ValidationError, create_model
from strands.types._events import ToolResultEvent
from strands.types.tools import AgentTool, ToolGenerator, ToolResult, ToolSpec, ToolUse

from .types import ToolOutput

RequiredMetadata = Mapping[str, str]
ToolCallable = Callable[..., Any]


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""

    return datetime.now(timezone.utc).isoformat()


def _is_json_serializable(value: Any) -> bool:
    """判断值是否可被 JSON 序列化。"""

    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return False
    return True


def _stringify_data(value: Any) -> str:
    """把工具结果转成可展示的文本。"""

    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if _is_json_serializable(value):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _normalize_common_failures(common_failures: Sequence[str] | str) -> list[str]:
    """把常见失败场景规范成字符串列表。"""

    if isinstance(common_failures, str):
        values = [common_failures]
    else:
        values = list(common_failures)

    cleaned = [item.strip() for item in values if isinstance(item, str) and item.strip()]
    if not cleaned:
        raise ValueError("common_failures 必须至少包含一条非空说明")
    return cleaned


def _normalize_tool_output(value: Any) -> ToolOutput:
    """把工具返回值收敛成统一 `ToolOutput` 结构。"""

    if isinstance(value, ToolOutput):
        return value

    if isinstance(value, str):
        return ToolOutput(data=value, model_text=value, preview=value)

    if _is_json_serializable(value):
        return ToolOutput(data=value, preview=_stringify_data(value))

    raise TypeError("工具返回值必须是 str、可 JSON 序列化对象或 ToolOutput")


def _tool_output_to_result(tool_use_id: str, output: ToolOutput, *, status: str = "success") -> ToolResult:
    """把公开 `ToolOutput` 转成 Strands 需要的 `ToolResult`。"""

    contents: list[dict[str, Any]] = []
    if output.data is not None and not isinstance(output.data, str):
        contents.append({"json": output.data})

    text = output.model_text
    if text is None and isinstance(output.data, str):
        text = output.data
    if text:
        contents.append({"text": text})

    if not contents and output.preview:
        contents.append({"text": output.preview})

    if not contents:
        contents.append({"text": "null"})

    return {
        "toolUseId": tool_use_id,
        "status": status,
        "content": contents,
    }


def _build_tool_description(
    *,
    purpose: str,
    when_to_use: str,
    parameters: Mapping[str, str],
    returns: str,
    common_failures: Sequence[str],
) -> str:
    """生成给底层模型看的工具描述文本。"""

    parameter_lines = "\n".join(f"- {name}: {description}" for name, description in parameters.items())
    failure_lines = "\n".join(f"- {item}" for item in common_failures)
    return (
        f"Purpose:\n{purpose}\n\n"
        f"When To Use:\n{when_to_use}\n\n"
        f"Parameters:\n{parameter_lines}\n\n"
        f"Returns:\n{returns}\n\n"
        f"Common Failures:\n{failure_lines}"
    )


@dataclass(slots=True)
class _ToolMetadata:
    """保存工具元数据与校验结果。"""

    name: str
    purpose: str
    when_to_use: str
    parameters: dict[str, str]
    returns: str
    common_failures: list[str]


class _EasyHarnessTool(AgentTool):
    """EasyHarness 私有工具实现。"""

    def __init__(self, func: ToolCallable, metadata: _ToolMetadata) -> None:
        """初始化工具并完成签名校验与 schema 推导。

        Args:
            func: 被包装的 Python 函数。
            metadata: 已归一化的工具元数据。
        """

        super().__init__()
        self._func = func
        self._metadata = metadata
        self._signature = inspect.signature(func)
        self._input_model = self._build_input_model()
        self._tool_spec = self._build_tool_spec()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """保留原函数的普通调用体验。"""

        return self._func(*args, **kwargs)

    @property
    def tool_name(self) -> str:
        """返回工具名。"""

        return self._metadata.name

    @property
    def tool_spec(self) -> ToolSpec:
        """返回底层运行时需要的工具描述。"""

        return self._tool_spec

    @property
    def tool_type(self) -> str:
        """声明当前实现为 Python 工具。"""

        return "python"

    def _build_input_model(self) -> type[Any]:
        """根据函数签名和类型注解构造输入模型。

        Returns:
            可用于校验工具输入的 Pydantic 模型。

        Raises:
            ValueError: 当元数据和函数签名不一致时抛出。
        """

        hints = get_type_hints(self._func)
        fields: dict[str, tuple[Any, Any]] = {}
        actual_parameters = list(self._signature.parameters.values())
        declared_names = set(self._metadata.parameters)
        actual_names = {parameter.name for parameter in actual_parameters}

        if declared_names != actual_names:
            missing = sorted(actual_names - declared_names)
            unknown = sorted(declared_names - actual_names)
            details: list[str] = []
            if missing:
                details.append(f"缺少参数文档: {', '.join(missing)}")
            if unknown:
                details.append(f"存在未知参数文档: {', '.join(unknown)}")
            raise ValueError("；".join(details))

        for parameter in actual_parameters:
            if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                raise ValueError("tool 不支持 *args 或 **kwargs")

            annotation = hints.get(parameter.name, parameter.annotation)
            if annotation is inspect.Parameter.empty:
                raise ValueError(f"参数 {parameter.name} 必须提供类型注解")

            default = ... if parameter.default is inspect.Parameter.empty else parameter.default
            fields[parameter.name] = (
                annotation,
                Field(default=default, description=self._metadata.parameters[parameter.name]),
            )

        model_name = f"{self._metadata.name.title().replace('_', '')}Input"
        return create_model(model_name, **fields)

    def _build_tool_spec(self) -> ToolSpec:
        """根据元数据和输入模型生成底层工具描述。"""

        schema = self._input_model.model_json_schema()
        schema.pop("title", None)
        for property_schema in schema.get("properties", {}).values():
            property_schema.pop("title", None)

        return {
            "name": self._metadata.name,
            "description": _build_tool_description(
                purpose=self._metadata.purpose,
                when_to_use=self._metadata.when_to_use,
                parameters=self._metadata.parameters,
                returns=self._metadata.returns,
                common_failures=self._metadata.common_failures,
            ),
            "inputSchema": {"json": schema},
        }

    async def _invoke(self, **kwargs: Any) -> Any:
        """兼容同步与异步工具函数调用。"""

        result = self._func(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def stream(self, tool_use: ToolUse, invocation_state: dict[str, Any], **kwargs: Any) -> ToolGenerator:
        """执行工具并发出开始/完成/失败事件。

        Args:
            tool_use: 本次工具调用请求。
            invocation_state: 当前调用上下文。
            **kwargs: 为兼容底层接口保留。

        Yields:
            工具生命周期事件，最后一个事件固定为 `ToolResultEvent`。
        """

        del kwargs
        tool_use_id = str(tool_use.get("toolUseId"))
        started_at = utc_now_iso()
        start = time.perf_counter()

        try:
            validated = self._input_model.model_validate(tool_use.get("input", {}))
        except ValidationError as error:
            duration_ms = int((time.perf_counter() - start) * 1000)
            message = error.json(ensure_ascii=False)
            yield {
                "easyharness_tool": {
                    "status": "failed",
                    "name": self.tool_name,
                    "tool_use_id": tool_use_id,
                    "started_at": started_at,
                    "duration_ms": duration_ms,
                    "error": message,
                }
            }
            yield ToolResultEvent(
                {
                    "toolUseId": tool_use_id,
                    "status": "error",
                    "content": [{"text": message}],
                },
                exception=error,
            )
            return

        arguments = validated.model_dump()
        yield {
            "easyharness_tool": {
                "status": "started",
                "name": self.tool_name,
                "tool_use_id": tool_use_id,
                "started_at": started_at,
                "input": arguments,
            }
        }

        try:
            raw_output = await self._invoke(**arguments)
            output = _normalize_tool_output(raw_output)
            invocation_state.setdefault("_easyharness_tool_outputs", {})[tool_use_id] = output
            duration_ms = int((time.perf_counter() - start) * 1000)
            yield {
                "easyharness_tool": {
                    "status": "completed",
                    "name": self.tool_name,
                    "tool_use_id": tool_use_id,
                    "started_at": started_at,
                    "duration_ms": duration_ms,
                    "output": asdict(output),
                }
            }
            yield ToolResultEvent(_tool_output_to_result(tool_use_id, output))
        except Exception as error:
            duration_ms = int((time.perf_counter() - start) * 1000)
            failed_output = ToolOutput(
                data={"error": str(error)},
                model_text=f"Error: {error}",
                preview=f"错误: {error}",
                detail=traceback.format_exc(),
            )
            invocation_state.setdefault("_easyharness_tool_outputs", {})[tool_use_id] = failed_output
            yield {
                "easyharness_tool": {
                    "status": "failed",
                    "name": self.tool_name,
                    "tool_use_id": tool_use_id,
                    "started_at": started_at,
                    "duration_ms": duration_ms,
                    "error": str(error),
                    "output": asdict(failed_output),
                }
            }
            yield ToolResultEvent(
                _tool_output_to_result(tool_use_id, failed_output, status="error"),
                exception=error,
            )


def tool(
    *,
    name: str,
    purpose: str,
    when_to_use: str,
    parameters: RequiredMetadata,
    returns: str,
    common_failures: Sequence[str] | str,
) -> Callable[[ToolCallable], _EasyHarnessTool]:
    """定义一个符合 EasyHarness 合同的工具。

    Args:
        name: 工具公开名字。
        purpose: 工具职责说明。
        when_to_use: 模型应在何时使用该工具。
        parameters: 参数名到中文/英文说明的映射，必须与函数签名完全一致。
        returns: 返回值语义说明。
        common_failures: 常见失败场景说明，可传字符串或字符串列表。

    Returns:
        返回一个可直接放入 `Agent(tools=[...])` 的工具对象。
    """

    metadata_values = {
        "name": name,
        "purpose": purpose,
        "when_to_use": when_to_use,
        "returns": returns,
    }
    for field_name, value in metadata_values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} 必须是非空字符串")

    parameter_docs = {key: value for key, value in dict(parameters).items()}
    if not parameter_docs or any(not key or not str(value).strip() for key, value in parameter_docs.items()):
        raise ValueError("parameters 必须为完整且非空的参数说明映射")

    normalized_failures = _normalize_common_failures(common_failures)

    metadata = _ToolMetadata(
        name=name.strip(),
        purpose=purpose.strip(),
        when_to_use=when_to_use.strip(),
        parameters={key: str(value).strip() for key, value in parameter_docs.items()},
        returns=returns.strip(),
        common_failures=normalized_failures,
    )

    def decorator(func: ToolCallable) -> _EasyHarnessTool:
        """把普通函数包装成 EasyHarness 工具。"""

        return _EasyHarnessTool(func, metadata)

    return decorator
