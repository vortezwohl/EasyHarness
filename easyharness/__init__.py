"""Minimal public SDK surface for EasyHarness.

The package exports Agent, AgentBusyError, ModelConfig, AgentEvent, ToolContext,
OptionalToolContext, ToolOutput, and tool. Runtime bridging, tool contract
validation, event mapping, and conversation compression remain in private modules.
"""

from ._internal.runtime import Agent
from ._internal.tools import tool
from ._internal.types import (
    AgentBusyError,
    AgentEvent,
    ModelConfig,
    OptionalToolContext,
    ToolContext,
    ToolOutput,
)

__all__ = [
    "Agent",
    "AgentBusyError",
    "ModelConfig",
    "AgentEvent",
    "ToolContext",
    "OptionalToolContext",
    "ToolOutput",
    "tool",
]

__AUTHOR__ = "吴子豪 / Vortez Wohl"
__EMAIL__ = "vortez.wohl@gmail.com"
__GITHUB__ = "https://github.com/vortezwohl"
__BLOG__ = "https://vortezwohl.github.io"
