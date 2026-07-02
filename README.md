<div align="center">
  <h1>EasyHarness</h1>
  <p>
    <strong>
      A minimal Python SDK for agent loops, with streaming events, clean tool contracts, and zero ceremony.
    </strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+" />
    <a href="https://github.com/vortezwohl/fileglide">
      <img src="https://img.shields.io/badge/fileglide-2563EB?logo=github&amp;logoColor=white" alt="FileGlide" />
    </a>
    <a href="https://github.com/strands-agents/harness-sdk">
      <img src="https://img.shields.io/badge/strands%20agents-0F766E?logo=github&amp;logoColor=white" alt="Strands Agents" />
    </a>
    <a href="https://github.com/BerriAI/litellm">
      <img src="https://img.shields.io/badge/litellm-7C3AED?logo=github&amp;logoColor=white" alt="LiteLLM" />
    </a>
  </p>
  <p>
    <sub>Small public surface. Strong defaults. Explicit control.</sub>
  </p>
</div>

## Why EasyHarness

EasyHarness is designed for local agent workflows where a tiny SDK surface
matters more than a large framework.

It works well for coding agents, but it is not limited to them. Any agent that
benefits from strict tool contracts, streaming events, and explicit runtime
control can use the same SDK surface.

It gives you:

- A single primary runtime entry point through `Agent`
- Strict tool metadata and output contracts through `tool` and `ToolOutput`
- A unified streaming event model for thinking, tool, assistant, compression,
  and system events
- An official FileGlide-backed filesystem toolset that can be auto-loaded by
  default or scoped explicitly

## Public Surface

The root package intentionally exposes only five public names:

- `Agent`
- `ModelConfig`
- `AgentEvent`
- `ToolOutput`
- `tool`

Everything else stays behind internal modules or the explicit
`easyharness.toolset` package.

## Installation

EasyHarness supports both `pip` and `uv`.

### Install with pip

```bash
pip install -U easyharness
```

### Install with uv

```bash
uv add -U easyharness
```

### Verify the installation

After installation, import the public package surface in Python:

```python
from easyharness import Agent, ModelConfig, AgentEvent, ToolOutput, tool
```

If the import succeeds, the SDK is ready to use.

## Typical Usage

### 1. Define a tool and run an agent

```python
from easyharness import Agent, ModelConfig, ToolOutput, tool


@tool(
    name="ping_tool",
    purpose="Return a fixed response for a minimal tool-flow check.",
    when_to_use=(
        "Use this when the model needs a trivial tool call to verify that the "
        "tool pipeline is available."
    ),
    parameters={},
    returns="A fixed pong response.",
    common_failures=["This tool does not fail under normal conditions."],
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
    system_prompt="You are a precise agent.",
    tools=[ping_tool],
)

print(agent.run("Call the ping tool and confirm that the tool pipeline works."))
```

### 2. Use the default FileGlide integration

`Agent` can auto-load the official FileGlide-backed toolset, so the shortest
agent setup does not need a manual `tools=[...]` list.

```python
from easyharness import Agent, ModelConfig


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="You are a careful agent.",
)

print(
    agent.run(
        "List the workspace, read pyproject.toml, and summarize the SDK shape."
    )
)
```

<details>
  <summary><strong>Official default FileGlide tools</strong></summary>

  <ul>
    <li><code>fileglide_list_tree</code></li>
    <li><code>fileglide_search_paths</code></li>
    <li><code>fileglide_read_text</code></li>
    <li><code>fileglide_search_text</code></li>
    <li><code>fileglide_edit_text</code></li>
    <li><code>fileglide_manage_paths</code></li>
    <li><code>fileglide_inspect_path</code></li>
  </ul>
</details>

### 3. Disable the default FileGlide tools

If you want a stricter default runtime with no filesystem tool auto-loading,
disable it explicitly.

```python
from easyharness import Agent, ModelConfig


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="You are a careful agent.",
    enable_fileglide=False,
)
```

### 4. Build a scoped official FileGlide toolset

When you need explicit control over the filesystem scope, disable the default
auto-load and pass a scoped official toolset from `easyharness.toolset`.

```python
from easyharness import Agent, ModelConfig
from easyharness.toolset import build_fileglide_tools


agent = Agent(
    model=ModelConfig(
        model="openai/gpt-4.1-mini",
        api_key="YOUR_API_KEY",
    ),
    system_prompt="You are a careful agent.",
    enable_fileglide=False,
    tools=build_fileglide_tools(default_root="D:/Projects/PythonProjects/EasyHarness"),
)
```

`build_fileglide_tools(default_root=...)` creates the official scoped toolset. Paths
that escape the configured root are rejected by FileGlide scope protection.

Each official `fileglide_*` tool also accepts an optional `root` argument for
that single call. When provided, it overrides the builder's default root
without additional SDK-level path-range restrictions.

```python
tools = build_fileglide_tools(default_root="D:/Projects/PythonProjects/EasyHarness")
tool_map = {tool.tool_name: tool for tool in tools}

result = tool_map["fileglide_read_text"](
    target="EasyHarness/pyproject.toml",
    root="D:/Projects/PythonProjects",
)
```

## Event Stream

`agent.stream(prompt)` yields a unified `AgentEvent` stream. The public event
kinds are:

- `thinking`
- `tool`
- `assistant`
- `compress`
- `system`

Each event uses the same status vocabulary:

- `started`
- `delta`
- `completed`
- `failed`

```python
for event in agent.stream("Inspect the workspace and explain the next step."):
    print(event.kind, event.status, event.text)
```

## Design Boundaries

EasyHarness is intentionally small. v1 does not try to solve:

- UI components
- Environment-variable orchestration layers
- Plugin platforms
- Multi-agent orchestration
- Root-package re-export sprawl for toolset builders

## Summary

EasyHarness is most useful when you want:

- A minimal `Agent` API
- Strict tool definitions
- Streaming runtime visibility
- A practical, official FileGlide-backed filesystem toolset

If that is your shape of problem, the shortest path is:

1. Create an `Agent`
2. Define tools with `@tool(...)`
3. Use the default FileGlide integration or pass a scoped official toolset
