# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Observed Facts
- ToolContext and OptionalToolContext currently use Annotated metadata in easyharness/_internal/types.py.
- easyharness/_internal/tools.py owns Context discovery, schema exclusion, direct calls, stream-time injection, and tool failures.
- easyharness/_internal/runtime.py currently treats optionality as part of a same-name cross-tool conflict.
- Existing tests prove schema hiding, per-invocation Context-map isolation, safe failures, legacy declaration rejection, optional None injection, and same-name conflict rejection.

## Approved Input Limits
- Support concrete classes, ABC parent classes, scalar runtime classes, and dict/list/tuple/set payloads, including recursive parameterized forms.
- Use recursive deep validation for parameterized containers.
- Reject payload unions at every level except the legacy outer ToolContext[T] | None syntax.
- Reject positional-only tool parameters and Context parameters preceding ordinary positional-or-keyword parameters.

## Compatibility Intent
Intentional breaking upgrade. Preserve ToolContext[T], OptionalToolContext[T], and legacy ToolContext[T] | None with a DeprecationWarning. Keep inheritance-based Context declarations unsupported.

## Functional Boundary
- Requested Functionality: Implement deep Context payload validation, source-default precedence, same-name type-only Agent contracts, and unified direct/Agent binding.
- Protected Functionality: Context remains hidden from model schemas and event inputs; invocation Context maps remain per-call; unknown Context names still fail early; non-Context tool behavior remains unchanged.
- Explicit Non-Goals: No IoC container, global state, plugin registry, static type-checker integration, payload coercion, broad typing-form support, or Python sandbox.
- Compatibility Guarantees: ToolContext[T] | None remains operational with a migration warning; current public exports remain available.
- Mandatory Stop Condition: Stop if implementation requires Context serialization, model visibility, a new dependency, positional-only support, payload unions, or a protected non-Context contract change.

## Preserved Contracts
- Host injection is keyed by declared parameter name.
- Context is omitted from metadata and Pydantic model input schemas.
- Failed Context injection does not execute the tool body or reveal the raw Context value.
- Each Agent invocation owns a separate private Context map.

## Explicitly Permitted Contract Changes
- Required and optional declarations with the same parameter name and equivalent payload become compatible.
- Source defaults take precedence over automatic optional None injection.
- Unsupported typing expressions and invalid Context ordering fail at tool registration.

## Execution Constraints
- Use the existing project dependencies only.
- Keep code, comments, docstrings, and documentation in English.
- Use dict() rather than empty dictionary literals in changed Python code.
- Run focused SDK tests before the full SDK test module.
