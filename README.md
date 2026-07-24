<div align="center">

<h1>
  <img src="assets/easyharness-wordmark.svg" alt="EasyHarness" width="520" />
</h1>

**Fast agents. Full control.**

*A compact Python SDK for strict tool contracts, observable streaming events, and scoped local file capabilities.*

[![PyPI](https://img.shields.io/pypi/v/easyharness?style=flat-square&color=00CFFF&label=PyPI)](https://pypi.org/project/easyharness/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-2563EB?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-B6FF00?style=flat-square&labelColor=07121F)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/vortezwohl/EasyHarness?style=flat-square&label=Stars)](https://github.com/vortezwohl/EasyHarness/stargazers)

<a href="https://github.com/vortezwohl/fileglide">
  <img src="https://img.shields.io/badge/FileGlide-2563EB?style=flat-square&logo=github&logoColor=white" alt="FileGlide" />
</a>
<a href="https://github.com/strands-agents/harness-sdk">
  <img src="https://img.shields.io/badge/Strands%20Agents-0F766E?style=flat-square&logo=github&logoColor=white" alt="Strands Agents" />
</a>
<a href="https://github.com/BerriAI/litellm">
  <img src="https://img.shields.io/badge/LiteLLM-7C3AED?style=flat-square&logo=github&logoColor=white" alt="LiteLLM" />
</a>

**One `Agent`. Strict tools. Every phase visible.**

[Why](#why-easyharness) &middot; [Quick start](#quick-start) &middot; [Capabilities](#core-capabilities) &middot; [Usage](#common-patterns) &middot; [API](#public-api) &middot; [Boundaries](#design-boundaries)

</div>

---

## Why EasyHarness

Most agent applications become difficult when tool behavior is vague, the UI cannot see real runtime phases, filesystem scope is unclear, and context failure arrives after the fact.

EasyHarness keeps those concerns in a small Python SDK. It is built for coding agents, but fits any single-agent workflow that needs reliable tool calls and observable execution.

| Where agents drift | What EasyHarness makes explicit |
| --- | --- |
| A tool is only a function, so the model does not know when to use it or how it fails. | `@tool` requires purpose, invocation guidance, parameter descriptions, return semantics, and common failures. |
| A product can only guess what an agent is doing. | `stream()` emits unified thinking, tool, assistant, compression, and system events. |
| Filesystem access is enabled without a legible boundary. | The official FileGlide toolset supports a default root and an explicit root per call. |
| Long sessions fail only after the model context overflows. | The default manager proactively compresses at 70% of the context window and reports the result as an event. |

## Quick Start

Run this from the project directory you want the agent to inspect. When no tools are supplied, `Agent` loads the official FileGlide toolset scoped to the current working directory.

```bash
pip install -U easyharness
```

```python
import os

from easyharness import Agent, ModelConfig


agent = Agent(
    model=ModelConfig(
        model="gpt-5.4",
        api_key=os.environ["OPENAI_API_KEY"],
    ),
    system_prompt="You are a careful code reviewer. Read files before answering.",
)

print(agent.run("Read README.md and pyproject.toml. List three core capabilities."))
```

This is the complete first loop: create a session-oriented agent, load filesystem tools, inspect the local project, and return text. The caller supplies the API key explicitly; EasyHarness does not read or orchestrate environment variables.

> [!TIP]
> With `uv`, run `uv add -U easyharness`. Configure the model ID, `base_url`, and context window through `ModelConfig`.

## Core Capabilities

| Capability | What you get |
| --- | --- |
| One runtime entry point | Use `Agent.run()` for final text or `Agent.stream()` for a live experience. |
| Strict tool contracts | Tool metadata, function signatures, and parameter documentation must agree. `ToolOutput` can serve both the model and a UI. |
| Host context injection | Pass runtime-only data with `ToolContext[T]` or `OptionalToolContext[T]`; it stays out of the model schema and receives deep type validation. |
| Observable events | One event vocabulary: `thinking`, `tool`, `assistant`, `compress`, and `system`. |
| Explicit session control | `cancel()` cooperatively stops the active call, `reset()` clears session history, and re-entry raises `AgentBusyError`. |
| Scoped file operations | Seven FileGlide tools cover listing, search, reading, editing, path management, and inspection. |
| Proactive compression | The default manager compresses at 70% of the context window, keeps eight recent messages, and emits its outcome. |
| OpenAI-compatible models | Supply a model ID, API key, `base_url`, sampling parameters, and a context-window override. A DeepSeek-compatible path preserves tool-call reasoning. |

## Common Patterns

### Define a strict tool

`@tool` does more than register a Python function. It produces a model-facing contract and rejects incomplete metadata before runtime.

```python
from easyharness import Agent, ModelConfig, ToolOutput, tool


@tool(
    name="get_build_status",
    purpose="Read the latest build status for a branch.",
    when_to_use="Use when the user asks whether the latest build passed on a specific branch.",
    parameters={"branch": "Branch whose latest build status should be read."},
    returns="A normalized build-status result for the requested branch.",
    common_failures=["No build record is available for the requested branch."],
)
def get_build_status(branch: str) -> ToolOutput:
    return ToolOutput(
        data={"branch": branch, "status": "passed"},
        model_text=f"The latest build for {branch} passed.",
        preview=f"{branch}: build passed",
        detail=f"Build status for {branch}: passed",
    )


agent = Agent(
    model=ModelConfig(model="gpt-5.4", api_key="YOUR_API_KEY"),
    system_prompt="You are a release assistant.",
    tools=[get_build_status],
    enable_fileglide=False,
)

print(agent.run("Did the latest build pass on main?"))
```

### Drive a live interface

`stream()` is the authoritative interface for a timeline, progress UI, or cancel control. Every event carries `kind`, `status`, timing information, and optional data.

```python
for event in agent.stream("Inspect the project and explain the next step."):
    print(event.kind, event.status, event.name, event.text)
```

The shared statuses are `started`, `delta`, `completed`, `failed`, and `cancelled`. On cancellation, the active phase ends as `cancelled`, the stream ends with `system/cancelled`, and the same `Agent` remains reusable.

```python
agent.cancel()  # A no-op while idle; requests cooperative cancellation while running.
agent.reset()   # Clears the current session history.
```

### Keep host data out of the model

Some values belong to your application and tool implementation, not to model-visible tool input: tenant identity, permission state, or a request object. Mark those arguments as `ToolContext[T]` or `OptionalToolContext[T]`; EasyHarness hides them from the schema and injects validated values on each `run()` or `stream()` call.

```python
from dataclasses import dataclass

from easyharness import Agent, ModelConfig, ToolContext, ToolOutput, tool


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str


@tool(
    name="tenant_summary",
    purpose="Read a requested summary section for the active tenant.",
    when_to_use="Use when the user asks for a specific summary section about the active tenant.",
    parameters={"section": "Summary section to retrieve."},
    returns="A summary for the requested section and active tenant.",
    common_failures=["The request context or summary section was not supplied."],
)
def tenant_summary(
    section: str,
    request: ToolContext[RequestContext],
) -> ToolOutput:
    return ToolOutput(
        model_text=f"{section} summary for active tenant: {request.tenant_id}"
    )


agent = Agent(
    model=ModelConfig(model="gpt-5.4", api_key="YOUR_API_KEY"),
    system_prompt="Call tenant_summary when the user asks for a specific summary section about the active tenant.",
    tools=[tenant_summary],
    enable_fileglide=False,
)

print(
    agent.run(
        "Show me the billing summary for my active tenant.",
        request=RequestContext(tenant_id="acme"),
    )
)
```

### Scope filesystem access

Build a scoped toolset when an agent should operate inside one project. Relative and absolute paths must remain within that root. To use another root for one call, pass an explicit `root`; `..` cannot escape the scope.

```python
from easyharness import Agent, ModelConfig
from easyharness.toolset import build_fileglide_tools


agent = Agent(
    model=ModelConfig(model="gpt-5.4", api_key="YOUR_API_KEY"),
    system_prompt="You are a careful local code assistant.",
    enable_fileglide=False,
    tools=build_fileglide_tools(default_root="D:/Projects/my-app"),
)
```

The official tools are `fileglide_list_tree`, `fileglide_search_paths`, `fileglide_read_text`, `fileglide_search_text`, `fileglide_edit_text`, `fileglide_manage_paths`, and `fileglide_inspect_path`.

### Tune model and context behavior

`ModelConfig` requires only `model` and `api_key`. Add `base_url`, `temperature`, `top_p`, `seed`, `context_window_limit`, or `extra_params` as needed. `extra_params` forwards additional LiteLLM request parameters, including OpenAI-compatible `extra_body`; explicit `temperature`, `top_p`, and a non-`None` `seed` take precedence over matching entries. It cannot override agent-owned request state, transport settings, credentials, or endpoints. When no context limit is provided, the SDK tries known model metadata before falling back to `200000`.

```python
model = ModelConfig(
    model="gpt-5.4",
    api_key="YOUR_API_KEY",
    extra_params={
        "max_tokens": 4096,
        "extra_body": {"provider_option": "value"},
    },
)
```

The default conversation manager uses `summary_ratio=0.3`, `preserve_recent_messages=8`, and a 70% proactive-compression threshold. Pass a custom `conversation_manager` to change that policy; compression start, completion, and failure appear as `compress` events.

## Public API

The root package deliberately exposes only eight names:

```python
from easyharness import (
    Agent,
    AgentBusyError,
    AgentEvent,
    ModelConfig,
    OptionalToolContext,
    ToolContext,
    ToolOutput,
    tool,
)
```

The file-tool builder lives in an explicit subpackage:

```python
from easyharness.toolset import build_fileglide_tools
```

## Design Boundaries

EasyHarness owns the single-agent runtime loop and its tool, session, and event contracts. It intentionally does not provide:

- UI components;
- environment-variable orchestration;
- a plugin platform;
- multi-agent orchestration; or
- broad root-package re-exports for every toolset builder.

That boundary keeps the SDK responsible for predictable runtime behavior while leaving product orchestration and experience design to the caller.

## Development

Sync the development environment, then run the SDK regression suite that does
not require real model credentials:

```bash
uv sync
uv run python -m unittest tests.test_sdk tests.test_context_window_resolution
```

## Contributing

Contributions should improve verifiable runtime behavior, tool contracts, event completeness, filesystem scope, or session control. Keep the public API narrow and add independently runnable tests for new behavior.

## License

[MIT](LICENSE)
