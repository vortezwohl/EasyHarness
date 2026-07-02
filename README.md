# EasyHarness

EasyHarness 是一个面向本地 coding agent 的极简 Python SDK。根包只公开 5 个顶层名字：

- `Agent`
- `ModelConfig`
- `AgentEvent`
- `ToolOutput`
- `tool`

默认情况下，`Agent` 会自动装载一组官方文件系统工具，覆盖常见的文件浏览、搜索、读取、编辑和检查场景。若你需要更严格的安全边界，可以显式禁用默认文件工具，或通过 `easyharness.toolset` 构建受控作用域的工具集。

## Quickstart

```python
from easyharness import Agent, ModelConfig


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="你是一个严谨的 coding agent。",
)

print(agent.run("先列出当前工作目录，再读取 README 并总结项目目标。"))
```

上面的最短路径不需要手动传 `tools`。`Agent` 会默认装载以下官方文件工具：

- `fileglide_list_tree`
- `fileglide_search_paths`
- `fileglide_read_text`
- `fileglide_search_text`
- `fileglide_edit_text`
- `fileglide_manage_paths`
- `fileglide_inspect_path`

## 自定义工具

```python
from easyharness import Agent, ModelConfig, ToolOutput, tool


@tool(
    name="ping_tool",
    purpose="返回固定文本，用于最小工具链验证。",
    when_to_use="当模型需要确认工具调用链可用时使用。",
    parameters={},
    returns="返回固定文本 pong。",
    common_failures=["不会失败"],
)
def ping_tool() -> ToolOutput:
    return ToolOutput(
        data={"value": "pong"},
        model_text="pong",
        preview="pong",
        detail='{"value": "pong"}',
    )


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="你是一个严谨的 coding agent。",
    tools=[ping_tool],
)
```

显式传入的工具会与默认文件工具合并；如果出现同名工具，调用方显式传入的工具优先。

## 禁用默认文件工具

```python
from easyharness import Agent, ModelConfig


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="你是一个严谨的 coding agent。",
    enable_fileglide=False,
)
```

这个配置适合对文件系统 I/O 更敏感的场景。

## 显式使用 `easyharness.toolset`

```python
from easyharness import Agent, ModelConfig
from easyharness.toolset import build_fileglide_tools


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="你是一个严谨的 coding agent。",
    enable_fileglide=False,
    tools=build_fileglide_tools(root="D:/Projects/PythonProjects/EasyHarness"),
)
```

`build_fileglide_tools(root=...)` 会返回一组绑定到指定根目录的官方文件工具，超出该根目录的路径会被作用域保护拒绝。

## Event Stream

`agent.stream(prompt)` 会持续产出 `AgentEvent`，公开事件种类固定为：

- `thinking`
- `tool`
- `assistant`
- `compress`
- `system`

每条事件都使用统一的 `started`、`delta`、`completed`、`failed` 状态语义。

## V1 Non-goals

v1 明确不做以下内容：

- UI 组件
- 环境变量配置系统
- 插件系统
- 多智能体 orchestration
- 根包级别的工具集导出扩张
