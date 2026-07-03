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

__AUTHOR__ = "Zihao Wu / Vortez Wohl"
__EMAIL__ = "vortez.wohl@gmail.com"
__GITHUB__ = "https://github.com/vortezwohl"
__BLOG__ = "https://vortezwohl.github.io"
