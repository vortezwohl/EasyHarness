"""Minimal public SDK surface for EasyHarness.

The package exports Agent, AgentBusyError, ModelConfig, AgentEvent, ToolContext,
OptionalToolContext, ToolOutput, tool, and two explicit conversation managers.
Runtime bridging, tool contract validation, and event mapping remain private.
"""

from strands.agent.conversation_manager import SlidingWindowConversationManager

from ._internal.conversation import EventingSummarizingConversationManager
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
    "EventingSummarizingConversationManager",
    "SlidingWindowConversationManager",
]

__AUTHOR__ = "吴子豪 / Vortez Wohl"
__EMAIL__ = "vortez.wohl@gmail.com"
__GITHUB__ = "https://github.com/vortezwohl"
__BLOG__ = "https://vortezwohl.github.io"
