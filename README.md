# EasyHarness

EasyHarness 是一个极简的 Python agent loop SDK。v1 只暴露五个顶层名字：
`Agent`、`ModelConfig`、`AgentEvent`、`ToolOutput` 和 `tool`。

## Quickstart

```python
from easyharness import Agent, ModelConfig, ToolOutput, tool


@tool(
    name="read_file",
    purpose="读取本地文本文件并返回内容摘要。",
    when_to_use="当你需要查看本地文件内容并提炼关键信息时使用。",
    parameters={"path": "要读取的 UTF-8 文本文件路径。"},
    returns="返回文件原文和适合 UI 展示的简要预览。",
    common_failures=["文件不存在", "文件不是 UTF-8 文本", "没有读取权限"],
)
def read_file(path: str) -> ToolOutput:
    with open(path, "r", encoding="utf-8") as file:
        text = file.read()
    return ToolOutput(
        data={"path": path, "length": len(text)},
        model_text=text,
        preview=f"{path} ({len(text)} chars)",
        detail=text,
    )


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="你是一个严谨的 coding agent。",
    tools=[read_file],
)

print(agent.run("请先读取 README，然后总结项目目标。"))

for event in agent.stream("继续分析测试覆盖情况。"):
    print(event)
```

## Event Stream

`agent.stream(prompt)` 会持续产出 `AgentEvent`，公开语义固定为：

- `thinking`
- `tool`
- `assistant`
- `compress`
- `system`

每条事件都使用统一的 `started`、`delta`、`completed`、`failed` 状态，不绑定任何 UI。

## V1 Non-goals

v1 明确不做以下内容：

- UI 组件
- 环境变量系统
- 插件系统
- 多智能体 orchestration
- 默认业务工具包
