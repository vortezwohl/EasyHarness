"""EasyHarness 的最小公开 SDK 表面。

包级入口仅导出 Agent、ModelConfig、AgentEvent、ToolContext、ToolOutput 和 tool。
运行时桥接、工具合同校验、事件映射和对话压缩均保留在私有模块中。
"""

from ._internal.runtime import Agent
from ._internal.tools import tool
from ._internal.types import AgentEvent, ModelConfig, ToolContext, ToolOutput

__all__ = ["Agent", "ModelConfig", "AgentEvent", "ToolContext", "ToolOutput", "tool"]

__AUTHOR__ = "Zihao Wu / Vortez Wohl"
__EMAIL__ = "vortez.wohl@gmail.com"
__GITHUB__ = "https://github.com/vortezwohl"
__BLOG__ = "https://vortezwohl.github.io"
