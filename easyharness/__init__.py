"""EasyHarness 的极简公开 SDK 表面。

该包只对外暴露五个常用名字：`Agent`、`ModelConfig`、`AgentEvent`、
`ToolOutput` 和 `tool`。其余运行时桥接、工具合同校验、事件映射与会话
压缩实现都收敛在私有模块中，普通调用方不需要接触内部对象。
"""

from ._internal.runtime import Agent
from ._internal.tools import tool
from ._internal.types import AgentEvent, ModelConfig, ToolOutput

__all__ = ["Agent", "ModelConfig", "AgentEvent", "ToolOutput", "tool"]
