"""Public data structures used by the EasyHarness SDK.

This module defines the externally visible structures for model configuration,
streaming events, and rich tool outputs. The runtime and tool contract logic
share these types to keep the public semantics stable.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Annotated, Literal


class AgentBusyError(RuntimeError):
    """Raised when a single-session Agent already has an active invocation."""


EventKind = Literal["thinking", "tool", "assistant", "compress", "system"]
EventStatus = Literal["started", "delta", "completed", "failed", "cancelled"]


def _copy_extra_param_value(value: object) -> object:
    """Copy standard mutable containers while preserving provider-specific leaves."""

    if isinstance(value, Mapping):
        return {
            key: _copy_extra_param_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_copy_extra_param_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_extra_param_value(item) for item in value)
    if isinstance(value, set):
        return {_copy_extra_param_value(item) for item in value}
    return value


def copy_extra_params(params: Mapping[str, object]) -> dict[str, object]:
    """Return an independent copy of standard extra-parameter containers."""

    return {
        name: _copy_extra_param_value(value)
        for name, value in params.items()
    }


class _FrozenParams(Mapping[str, object]):
    """Pickle-safe mapping that prevents mutation of stored model parameters."""

    def __init__(self, values: Mapping[str, object]) -> None:
        """Store an independent snapshot of standard mutable containers."""

        self._values = copy_extra_params(values)

    def __getitem__(self, name: str) -> object:
        """Return an independent copy so nested containers cannot mutate state."""

        return _copy_extra_param_value(self._values[name])

    def __iter__(self) -> Iterator[str]:
        """Iterate parameter names without exposing mutable values."""

        return iter(self._values)

    def __len__(self) -> int:
        """Return the number of stored parameters."""

        return len(self._values)

    def __reduce__(self) -> tuple[type[_FrozenParams], tuple[dict[str, object]]]:
        """Reconstruct the immutable mapping from serializable parameter data."""

        return type(self), (copy_extra_params(self),)

    def __deepcopy__(self, memo: dict[int, object]) -> _FrozenParams:
        """Create another immutable snapshot for copy and dataclass helpers."""

        copied = type(self)(self)
        memo[id(self)] = copied
        return copied


@dataclass(frozen=True, slots=True)
class _ToolContextAnnotation:
    """Store private metadata for one host-injected tool parameter."""

    optional: bool


class ToolContext:
    """Declare one required host-injected tool Context parameter.

    Use ``ToolContext[PayloadType]`` in a tool signature. ``PayloadType`` stays a
    normal application type and must not inherit from this annotation helper.
    """

    def __new__(cls, *args: object, **kwargs: object) -> ToolContext:
        """Reject runtime construction because this type exists only for annotations."""

        del args, kwargs
        raise TypeError("ToolContext is annotation-only; use ToolContext[PayloadType]")

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject the removed inheritance-based Context declaration contract."""

        del kwargs
        raise TypeError(
            "ToolContext cannot be subclassed; use ToolContext[PayloadType]"
        )

    def __class_getitem__(cls, payload_type: object) -> object:
        """Attach required Context metadata to one payload type annotation."""

        return Annotated[payload_type, _ToolContextAnnotation(optional=False)]


class OptionalToolContext:
    """Declare one optional host-injected tool Context parameter.

    Use ``OptionalToolContext[PayloadType]`` when omitted host injection must
    resolve to ``None`` for runtime and direct decorated-tool calls.
    """

    def __new__(cls, *args: object, **kwargs: object) -> OptionalToolContext:
        """Reject runtime construction because this type exists only for annotations."""

        del args, kwargs
        raise TypeError(
            "OptionalToolContext is annotation-only; "
            "use OptionalToolContext[PayloadType]"
        )

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subclassing because optional Context is annotation-only syntax."""

        del kwargs
        raise TypeError(
            "OptionalToolContext cannot be subclassed; "
            "use OptionalToolContext[PayloadType]"
        )

    def __class_getitem__(cls, payload_type: object) -> object:
        """Attach optional Context metadata to one nullable payload annotation."""

        return Annotated[
            payload_type | None,
            _ToolContextAnnotation(optional=True),
        ]


@dataclass(slots=True, frozen=True)
class ModelConfig:
    """Explicit model settings for a single agent session.

    Args:
        model: Model name passed directly to the underlying client.
        api_key: API key used for requests made by this model.
        base_url: OpenAI-compatible endpoint, defaulting to the official URL.
        temperature: Sampling temperature with a deliberately low default.
        top_p: Nucleus sampling parameter with a deliberately low default.
        seed: Optional random seed; falls back to provider defaults when unset.
        context_window_limit: Optional explicit context window override used
            when the caller knows the real model capacity.
        extra_params: Additional LiteLLM request parameters. Explicit fields
            such as temperature, top_p, and a non-None seed take precedence.
            The extra_body value, when supplied, must be a string-keyed mapping.
    """

    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    temperature: float = .01
    top_p: float = .01
    seed: int | None = None
    context_window_limit: int | None = None
    extra_params: Mapping[str, object] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        """Validate and snapshot caller-supplied upstream request parameters.

        Standard mutable containers are copied recursively and the resulting
        mapping rejects mutation. Provider-specific object values remain opaque.
        """

        if not isinstance(self.extra_params, Mapping):
            raise TypeError("extra_params must be a mapping")

        extra_params = dict(self.extra_params)
        if any(not isinstance(name, str) for name in extra_params):
            raise TypeError("extra_params keys must be strings")

        extra_body = extra_params.get("extra_body")
        if extra_body is not None:
            if not isinstance(extra_body, Mapping):
                raise TypeError("extra_params['extra_body'] must be a mapping")
            if any(not isinstance(name, str) for name in extra_body):
                raise TypeError("extra_params['extra_body'] keys must be strings")
        object.__setattr__(self, "extra_params", _FrozenParams(extra_params))


@dataclass(slots=True, frozen=True)
class ToolOutput:
    """Rich tool output for both model consumption and UI rendering.

    Args:
        data: Structured raw payload, primarily meant for programmatic use.
        model_text: Text fed back to the model for subsequent reasoning.
        preview: Short preview shown in timeline or list views.
        detail: Expanded details for inspector or debugging views.
    """

    data: object | None = None
    model_text: str | None = None
    preview: str | None = None
    detail: str | None = None


@dataclass(slots=True, frozen=True)
class AgentEvent:
    """Unified public event structure.

    Args:
        kind: Event category such as thinking, tool, or assistant.
        status: Event phase such as started, delta, completed, failed, or
            cancelled.
        text: Text attached to the event; usually incremental for delta events.
        name: Related object name, for example the tool name.
        started_at: ISO 8601 timestamp for when the phase started.
        duration_ms: Duration in milliseconds for completed, failed, or
            cancelled events.
        data: Extra payload carrying tool details, compression mode, and more.
    """

    kind: EventKind
    status: EventStatus
    text: str | None = None
    name: str | None = None
    started_at: str | None = None
    duration_ms: int | None = None
    data: object | None = None
