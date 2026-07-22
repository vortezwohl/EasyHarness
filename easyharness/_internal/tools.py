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
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from types import UnionType
from typing import (
    Annotated,
    Any,
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

from easyharness._internal.types import ToolOutput, _ToolContextAnnotation

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
    """Describe one hidden Context parameter resolved for a tool invocation."""

    name: str
    payload_annotation: object
    nullable: bool
    default: object
    kind: inspect._ParameterKind


class _ToolContextInjectionError(ValueError):
    """Represent a safe injection failure that does not expose a Context value."""


def _tool_context_annotation(annotation: object) -> tuple[object, bool] | None:
    """Recognize and validate annotation-based host Context declarations."""

    direct_context = _direct_tool_context_annotation(annotation)
    if direct_context is not None:
        return direct_context

    if get_origin(annotation) not in (Union, UnionType):
        return None

    arguments = get_args(annotation)
    context_arguments = [
        argument
        for argument in arguments
        if _direct_tool_context_annotation(argument) is not None
    ]
    if not context_arguments:
        return None
    if (
        len(arguments) != 2
        or type(None) not in arguments
        or len(context_arguments) != 1
    ):
        raise ValueError(
            "Tool Context parameters cannot use unions with multiple concrete types; "
            "use ToolContext[PayloadType] or OptionalToolContext[PayloadType]"
        )

    payload_annotation, optional = _direct_tool_context_annotation(context_arguments[0])
    if optional:
        raise ValueError(
            "OptionalToolContext[PayloadType] must not be unioned with None; "
            "use OptionalToolContext[PayloadType] directly"
        )
    warnings.warn(
        "ToolContext[PayloadType] | None is deprecated; "
        "use OptionalToolContext[PayloadType] instead",
        DeprecationWarning,
        stacklevel=3,
    )
    return payload_annotation, True


def _direct_tool_context_annotation(annotation: object) -> tuple[object, bool] | None:
    """Extract one validated Context payload annotation and optionality marker."""

    if get_origin(annotation) is not Annotated:
        return None
    arguments = get_args(annotation)
    if not arguments:
        return None
    markers = [
        argument
        for argument in arguments[1:]
        if isinstance(argument, _ToolContextAnnotation)
    ]
    if len(markers) != 1:
        return None

    payload_annotation = arguments[0]
    marker = markers[0]
    if marker.optional:
        payload_annotation = _optional_context_payload_annotation(payload_annotation)
    _validate_tool_context_payload_annotation(payload_annotation)
    return payload_annotation, marker.optional


def _optional_context_payload_annotation(annotation: object) -> object:
    """Extract the concrete payload annotation from an optional Context marker."""

    if get_origin(annotation) not in (Union, UnionType):
        raise ValueError(
            "OptionalToolContext[PayloadType] requires a nullable payload annotation"
        )
    arguments = get_args(annotation)
    if len(arguments) != 2 or type(None) not in arguments:
        raise ValueError(
            "OptionalToolContext[PayloadType] requires exactly one concrete "
            "payload type"
        )
    return next(argument for argument in arguments if argument is not type(None))


def _validate_tool_context_payload_annotation(annotation: object) -> None:
    """Reject payload annotations outside the approved runtime-checkable grammar."""

    if annotation is object:
        return
    if annotation is Any or annotation is type(None):
        raise ValueError(
            "Tool Context payload types must be concrete classes "
            "or supported containers"
        )

    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        raise ValueError(
            "ToolContext[PayloadType] requires one concrete payload type "
            "and cannot contain unions; use "
            "OptionalToolContext[PayloadType] for optional injection"
        )
    if origin is dict:
        arguments = get_args(annotation)
        if len(arguments) != 2:
            raise ValueError("Tool Context dict payloads require key and value types")
        for argument in arguments:
            _validate_tool_context_payload_annotation(argument)
        return
    if origin in (list, set):
        arguments = get_args(annotation)
        if len(arguments) != 1:
            raise ValueError("Tool Context list and set payloads require one item type")
        _validate_tool_context_payload_annotation(arguments[0])
        return
    if origin is tuple:
        arguments = get_args(annotation)
        if annotation == tuple[()]:
            raise ValueError("Tool Context empty fixed tuple payloads are unsupported")
        if not arguments:
            return
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            _validate_tool_context_payload_annotation(arguments[0])
            return
        for argument in arguments:
            _validate_tool_context_payload_annotation(argument)
        return
    if origin is not None:
        raise ValueError(
            "Tool Context payload types must be concrete classes "
            "or supported containers"
        )
    if not isinstance(annotation, type) or getattr(annotation, "_is_protocol", False):
        raise ValueError(
            "Tool Context payload types must be concrete classes "
            "or supported containers"
        )


def _context_value_matches(
    value: object,
    annotation: object,
    active_pairs: set[tuple[int, int]] | None = None,
) -> bool:
    """Return whether one Context value matches a supported payload annotation."""

    if annotation is object:
        return True

    origin = get_origin(annotation)
    if origin is None:
        return isinstance(value, annotation)
    if not isinstance(value, origin):
        return False

    arguments = get_args(annotation)
    if not arguments:
        return True

    if active_pairs is None:
        active_pairs = set()
    pair = (id(value), id(annotation))
    if pair in active_pairs:
        return True
    active_pairs.add(pair)
    try:
        if origin is dict:
            key_annotation, value_annotation = arguments
            return all(
                _context_value_matches(key, key_annotation, active_pairs)
                and _context_value_matches(item, value_annotation, active_pairs)
                for key, item in value.items()
            )
        if origin in (list, set):
            item_annotation = arguments[0]
            return all(
                _context_value_matches(item, item_annotation, active_pairs)
                for item in value
            )
        if origin is tuple:
            if len(arguments) == 2 and arguments[1] is Ellipsis:
                return all(
                    _context_value_matches(item, arguments[0], active_pairs)
                    for item in value
                )
            if len(value) != len(arguments):
                return False
            return all(
                _context_value_matches(item, item_annotation, active_pairs)
                for item, item_annotation in zip(value, arguments)
            )
    finally:
        active_pairs.remove(pair)
    return False


def _context_payload_description(annotation: object) -> str:
    """Return a safe descriptive label for one expected Context payload."""

    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def _validate_context_value(
    tool_name: str,
    parameter: _ToolContextParameter,
    value: object,
    error_type: type[Exception],
) -> None:
    """Validate a resolved Context value without exposing the raw value."""

    if value is None and parameter.nullable:
        return
    if not _context_value_matches(value, parameter.payload_annotation):
        raise error_type(
            f"Tool {tool_name} requires Context parameter {parameter.name} of type "
            f"{_context_payload_description(parameter.payload_annotation)}"
        )
    if (
        value is None
        and not parameter.nullable
        and parameter.payload_annotation is object
    ):
        warnings.warn(
            "ToolContext[object] received None; use OptionalToolContext[object] "
            "when None represents optional host injection",
            RuntimeWarning,
            stacklevel=4,
        )


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
        self._type_hints = get_type_hints(func, include_extras=True)
        self._context_parameters = self._build_context_parameters()
        self._input_model = self._build_input_model()
        self._tool_spec = self._build_tool_spec()
        self.__signature__ = self._direct_call_signature()

    def __call__(self, *args: object, **kwargs: object) -> object:
        """Call the original function with resolved direct Context arguments."""

        bound_arguments = self.__signature__.bind_partial(*args, **kwargs)
        for parameter in self._context_parameters:
            if parameter.name not in bound_arguments.arguments:
                if parameter.default is not inspect.Parameter.empty:
                    value = parameter.default
                elif parameter.nullable:
                    value = None
                else:
                    raise TypeError(
                        f"Tool {self.tool_name} requires Context parameter "
                        f"{parameter.name} of type "
                        f"{_context_payload_description(parameter.payload_annotation)}"
                    )
                bound_arguments.arguments[parameter.name] = value
            _validate_context_value(
                self.tool_name,
                parameter,
                bound_arguments.arguments[parameter.name],
                TypeError,
            )
        return self._func(*bound_arguments.args, **bound_arguments.kwargs)

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
        """Extract and validate non-model Context parameters from a signature."""

        parameters: list[_ToolContextParameter] = []
        context_seen = False
        for parameter in self._signature.parameters.values():
            if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
                raise ValueError("tool does not support positional-only parameters")
            if parameter.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                raise ValueError("tool does not support *args or **kwargs")

            annotation = self._type_hints.get(parameter.name, parameter.annotation)
            context_annotation = _tool_context_annotation(annotation)
            if context_annotation is None:
                if (
                    context_seen
                    and parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
                ):
                    raise ValueError(
                        "Tool Context parameters must follow ordinary "
                        "positional parameters"
                    )
                continue

            if parameter.name == "prompt":
                raise ValueError(
                    "Tool Context parameter name 'prompt' is reserved by "
                    "Agent.run() and Agent.stream()"
                )

            context_seen = True
            payload_annotation, nullable = context_annotation
            if (
                parameter.default is not inspect.Parameter.empty
                and not (parameter.default is None and nullable)
                and not _context_value_matches(parameter.default, payload_annotation)
            ):
                raise ValueError(
                    f"Default for Context parameter {parameter.name} must match "
                    f"{_context_payload_description(payload_annotation)}"
                )
            parameters.append(
                _ToolContextParameter(
                    name=parameter.name,
                    payload_annotation=payload_annotation,
                    nullable=nullable,
                    default=parameter.default,
                    kind=parameter.kind,
                )
            )
        return tuple(parameters)

    def _direct_call_signature(self) -> inspect.Signature:
        """Expose source defaults and optional Context fallbacks to callers."""

        context_parameters = dict(
            (parameter.name, parameter) for parameter in self._context_parameters
        )
        parameters = [
            parameter.replace(default=None)
            if context_parameters.get(parameter.name, None) is not None
            and context_parameters[parameter.name].nullable
            and context_parameters[parameter.name].default is inspect.Parameter.empty
            else parameter
            for parameter in self._signature.parameters.values()
        ]
        return inspect.Signature(
            parameters=parameters,
            return_annotation=self._signature.return_annotation,
            __validate_parameters__=False,
        )

    def _resolve_context_arguments(
        self,
        invocation_state: dict[str, object],
    ) -> dict[str, object]:
        """Resolve and validate private Context values before invocation."""

        raw_contexts = invocation_state.get("_easyharness_tool_contexts", dict())
        if not isinstance(raw_contexts, Mapping):
            raise _ToolContextInjectionError(
                f"Tool {self.tool_name} received an invalid private context map"
            )
        resolved: dict[str, object] = dict()
        for parameter in self._context_parameters:
            if parameter.name in raw_contexts:
                value = raw_contexts[parameter.name]
            elif parameter.default is not inspect.Parameter.empty:
                value = parameter.default
            elif parameter.nullable:
                value = None
            else:
                raise _ToolContextInjectionError(
                    f"Tool {self.tool_name} requires Context parameter "
                    f"{parameter.name} of type "
                    f"{_context_payload_description(parameter.payload_annotation)}"
                )
            _validate_context_value(
                self.tool_name,
                parameter,
                value,
                _ToolContextInjectionError,
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

        fields: dict[str, tuple[object, object]] = dict()
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
        for property_schema in schema.get("properties", dict()).values():
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

        tool_outputs = invocation_state.setdefault("_easyharness_tool_outputs", dict())
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
            validated = self._input_model.model_validate(tool_use.get("input", dict()))
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
    if any(not key or not str(value).strip() for key, value in parameter_docs.items()):
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
