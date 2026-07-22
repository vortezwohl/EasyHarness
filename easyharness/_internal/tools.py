"""Strict tool contract implementation for EasyHarness.

This module exposes the public `tool` decorator and folds function signatures,
type hints, parameter docs, and runtime outputs into an internal `AgentTool`.
Callers only need to write ordinary Python functions with complete metadata
instead of touching the native Strands decorator or private contract objects.
"""

from __future__ import annotations

import inspect
import json
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from types import UnionType
from typing import (
    Callable,
    Mapping,
    Sequence,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel, Field, ValidationError, create_model
from strands.types._events import ToolResultEvent
from strands.types.tools import AgentTool, ToolGenerator, ToolResult, ToolSpec, ToolUse

from easyharness._internal.types import ToolContext, ToolOutput

RequiredMetadata = Mapping[str, str]
ToolCallable = Callable[..., object]


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""

    return datetime.now(timezone.utc).isoformat()


def _is_json_serializable(value: object) -> bool:
    """Return whether a value can be serialized as JSON."""

    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return False
    return True


def _stringify_data(value: object) -> str:
    """Render tool output as displayable text."""

    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if _is_json_serializable(value):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _normalize_common_failures(common_failures: Sequence[str] | str) -> list[str]:
    """Normalize common failure descriptions into a list of strings."""

    if isinstance(common_failures, str):
        values = [common_failures]
    else:
        values = list(common_failures)

    cleaned = [
        item.strip() for item in values if isinstance(item, str) and item.strip()
    ]
    if not cleaned:
        raise ValueError("common_failures must contain at least one non-empty item")
    return cleaned


def _normalize_tool_output(value: object) -> ToolOutput:
    """Normalize tool return values into a unified `ToolOutput`."""

    if isinstance(value, ToolOutput):
        return value

    if isinstance(value, str):
        return ToolOutput(data=value, model_text=value, preview=value)

    if _is_json_serializable(value):
        return ToolOutput(data=value, preview=_stringify_data(value))

    raise TypeError(
        "Tool return values must be str, JSON-serializable objects, or ToolOutput"
    )


def _tool_output_to_result(
    tool_use_id: str,
    output: ToolOutput,
    *,
    status: str = "success",
) -> ToolResult:
    """Convert public `ToolOutput` into the `ToolResult` expected by Strands."""

    contents: list[dict[str, object]] = []
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
    """Build the tool description shown to the underlying model."""

    parameter_lines = "\n".join(
        f"- {name}: {description}" for name, description in parameters.items()
    )
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
    """Store normalized tool metadata and validation results."""

    name: str
    purpose: str
    when_to_use: str
    parameters: dict[str, str]
    returns: str
    common_failures: list[str]


@dataclass(frozen=True, slots=True)
class _ToolContextParameter:
    """Describe a hidden Context parameter resolved per invocation.

    The specification is derived from the function signature.
    """

    name: str
    context_type: type[ToolContext]
    nullable: bool
    default: object


def _tool_context_annotation(
    annotation: object,
) -> tuple[type[ToolContext], bool] | None:
    """Recognize ToolContext annotations that may be hidden from model input."""

    if isinstance(annotation, type) and issubclass(annotation, ToolContext):
        return annotation, False
    if get_origin(annotation) not in (Union, UnionType):
        return None
    arguments = get_args(annotation)
    if len(arguments) != 2 or type(None) not in arguments:
        return None
    context_type = next(
        argument for argument in arguments if argument is not type(None)
    )
    if isinstance(context_type, type) and issubclass(context_type, ToolContext):
        return context_type, True
    return None


class _ToolContextInjectionError(ValueError):
    """Represent a safe injection failure that does not expose a Context value."""


class _EasyHarnessTool(AgentTool):
    """Private EasyHarness tool implementation."""

    def __init__(self, func: ToolCallable, metadata: _ToolMetadata) -> None:
        """Initialize the tool and derive its validated schema.

        Args:
            func: Wrapped Python function.
            metadata: Normalized tool metadata.
        """

        super().__init__()
        self._func = func
        self._metadata = metadata
        self._signature = inspect.signature(func)
        self._type_hints = get_type_hints(func)
        self._context_parameters = self._build_context_parameters()
        self._input_model = self._build_input_model()
        self._tool_spec = self._build_tool_spec()

    def __call__(self, *args: object, **kwargs: object) -> object:
        """Preserve the ordinary call experience of the original function."""

        return self._func(*args, **kwargs)

    @property
    def tool_name(self) -> str:
        """Return the tool name."""

        return self._metadata.name

    @property
    def tool_spec(self) -> ToolSpec:
        """Return the tool description required by the runtime."""

        return self._tool_spec

    @property
    def tool_type(self) -> str:
        """Declare that this implementation is a Python tool."""

        return "python"

    @property
    def context_parameters(self) -> tuple[_ToolContextParameter, ...]:
        """Return hidden Context parameter specifications in signature order."""

        return self._context_parameters

    def _build_context_parameters(self) -> tuple[_ToolContextParameter, ...]:
        """Extract non-model Context parameters from a function signature.

        The returned specifications retain their declaration order.
        """

        parameters: list[_ToolContextParameter] = []
        for parameter in self._signature.parameters.values():
            annotation = self._type_hints.get(parameter.name, parameter.annotation)
            context_annotation = _tool_context_annotation(annotation)
            if context_annotation is None:
                continue
            context_type, nullable = context_annotation
            parameters.append(
                _ToolContextParameter(
                    name=parameter.name,
                    context_type=context_type,
                    nullable=nullable,
                    default=parameter.default,
                )
            )
        return tuple(parameters)

    def _resolve_context_arguments(
        self,
        invocation_state: dict[str, object],
    ) -> dict[str, object]:
        """Resolve and validate private Context values before invocation.

        Values are matched by the hidden parameter name.
        """

        raw_contexts = invocation_state.get("_easyharness_tool_contexts", {})
        if not isinstance(raw_contexts, Mapping):
            raise _ToolContextInjectionError(
                f"Tool {self.tool_name} received an invalid private context map"
            )
        resolved: dict[str, object] = {}
        for parameter in self._context_parameters:
            if parameter.name not in raw_contexts:
                if (
                    parameter.nullable
                    and parameter.default is not inspect.Parameter.empty
                ):
                    continue
                raise _ToolContextInjectionError(
                    f"Tool {self.tool_name} requires Context parameter "
                    f"{parameter.name} of type "
                    f"{parameter.context_type.__name__}"
                )
            value = raw_contexts[parameter.name]
            if value is None and parameter.nullable:
                resolved[parameter.name] = value
                continue
            if not isinstance(value, parameter.context_type):
                raise _ToolContextInjectionError(
                    f"Tool {self.tool_name} requires Context parameter "
                    f"{parameter.name} of type "
                    f"{parameter.context_type.__name__}"
                )
            resolved[parameter.name] = value
        return resolved

    def _build_input_model(self) -> type[BaseModel]:
        """Build an input model from the function signature and type hints.

        Returns:
            Pydantic model used to validate tool input.

        Raises:
            ValueError: Raised when metadata and signature do not match.
        """

        fields: dict[str, tuple[object, object]] = {}
        context_names = {parameter.name for parameter in self._context_parameters}
        actual_parameters = [
            parameter
            for parameter in self._signature.parameters.values()
            if parameter.name not in context_names
        ]
        declared_names = set(self._metadata.parameters)
        actual_names = {parameter.name for parameter in actual_parameters}

        if declared_names != actual_names:
            missing = sorted(actual_names - declared_names)
            unknown = sorted(declared_names - actual_names)
            details: list[str] = []
            if missing:
                details.append(f"Missing parameter docs: {', '.join(missing)}")
            if unknown:
                details.append(f"Unexpected parameter docs: {', '.join(unknown)}")
            raise ValueError("; ".join(details))

        for parameter in actual_parameters:
            if parameter.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                raise ValueError("tool does not support *args or **kwargs")

            annotation = self._type_hints.get(parameter.name, parameter.annotation)
            if annotation is inspect.Parameter.empty:
                raise ValueError(
                    f"Parameter {parameter.name} must provide a type annotation"
                )

            default = (
                ...
                if parameter.default is inspect.Parameter.empty
                else parameter.default
            )
            fields[parameter.name] = (
                annotation,
                Field(
                    default=default,
                    description=self._metadata.parameters[parameter.name],
                ),
            )

        model_name = f"{self._metadata.name.title().replace('_', '')}Input"
        return create_model(model_name, **fields)

    def _build_tool_spec(self) -> ToolSpec:
        """Generate the runtime tool specification from metadata and schema."""

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

    async def _invoke(self, **kwargs: object) -> object:
        """Handle both synchronous and asynchronous tool functions."""

        result = self._func(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _tool_outputs_store(
        invocation_state: dict[str, object],
    ) -> dict[str, ToolOutput]:
        """Return the context dictionary used to cache tool outputs."""

        tool_outputs = invocation_state.setdefault("_easyharness_tool_outputs", {})
        return cast(dict[str, ToolOutput], tool_outputs)

    async def stream(
        self,
        tool_use: ToolUse,
        invocation_state: dict[str, object],
        **kwargs: object,
    ) -> ToolGenerator:
        """Execute the tool and emit started/completed/failed events.

        Args:
            tool_use: Current tool invocation request.
            invocation_state: Current invocation context.
            **kwargs: Reserved for compatibility with the underlying API.

        Yields:
            Tool lifecycle events, ending with a `ToolResultEvent`.
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
            call_arguments = {
                **arguments,
                **self._resolve_context_arguments(invocation_state),
            }
            raw_output = await self._invoke(**call_arguments)
            output = _normalize_tool_output(raw_output)
            self._tool_outputs_store(invocation_state)[tool_use_id] = output
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
                preview=f"Error: {error}",
                detail=traceback.format_exc(),
            )
            self._tool_outputs_store(invocation_state)[tool_use_id] = failed_output
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
    """Define a tool that satisfies the EasyHarness contract.

    Args:
        name: Public tool name.
        purpose: Purpose description for the tool.
        when_to_use: Guidance for when the model should use this tool.
        parameters: Mapping from parameter name to description; it must match
            the function signature exactly.
        returns: Return value semantics.
        common_failures: Common failure descriptions as one string or a list.

    Returns:
        Tool object ready to be passed into `Agent(tools=[...])`.
    """

    metadata_values = {
        "name": name,
        "purpose": purpose,
        "when_to_use": when_to_use,
        "returns": returns,
    }
    for field_name, value in metadata_values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    parameter_docs = {key: value for key, value in dict(parameters).items()}
    if any(
        not key or not str(value).strip() for key, value in parameter_docs.items()
    ):
        raise ValueError(
            "parameters must be a complete mapping of non-empty descriptions"
        )

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
        """Wrap a normal function as an EasyHarness tool."""

        return _EasyHarnessTool(func, metadata)

    return decorator
