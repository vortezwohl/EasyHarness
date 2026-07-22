# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Observed Facts
- _EasyHarnessTool owns the callable, signature, metadata, input model, and invocation-state execution seam.
- Strands supports per-call invocation_state for synchronous and streaming calls.
- Existing tool events publish model arguments as public input, so injection kwargs must stay separate.

## Public Contract
- Export an empty ToolContext marker class.
- ToolContext subtype annotations identify hidden tool parameters, including legal optional unions.
- Agent.run(prompt, **tool_contexts) and Agent.stream(prompt, **tool_contexts) accept Context keyed by function parameter name.
- Context is absent from metadata, schema, tool descriptions, model messages, ToolResult, and default event input.

## Lifecycle Contract
Each invocation creates a private mapping passed by reference only through invocation_state. Resolve Context only if the corresponding tool is invoked. No Agent, Tool, or module state retains it.

## Failure and Visibility Contract
Unknown Context keys fail before invocation. Missing or wrong Context fails only the invoked tool without executing user code. Error text contains only tool name, parameter name, and expected type name; user-returned ToolOutput remains unchanged.

## Compatibility Obligations
Existing decorators, old prompt-only calls, ordinary schemas, zero-argument tools, direct Python calls, event shape, and session reuse remain compatible.