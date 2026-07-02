"""Minimal public SDK surface for EasyHarness.

The package exposes only five public names: `Agent`, `ModelConfig`,
`AgentEvent`, `ToolOutput`, and `tool`. Runtime bridging, tool contract
validation, event mapping, and conversation compression stay inside private
modules so ordinary callers never have to touch internal objects.
"""

from ._internal.runtime import Agent
from ._internal.tools import tool
from ._internal.types import AgentEvent, ModelConfig, ToolOutput

__all__ = ["Agent", "ModelConfig", "AgentEvent", "ToolOutput", "tool"]
