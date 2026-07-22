# Context and Contract

## Metadata
- Document Type: Context and Contract
- Document ID: CONTEXT
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Observed Facts
- `ToolContext` is currently a base class marker and Context recognition depends on subclass checks.
- The current parser recognizes only a Context subclass or a two-member union with `None`.
- A Context union with another concrete type falls through to model-input processing instead of failing during tool registration.
- Optional Context omission currently depends on the original function declaring a default value.
- `Agent.run()` and `Agent.stream()` build invocation state, while direct calls to decorated tools bypass Context injection.

## Approved Input Limits
- Each Context parameter maps to exactly one runtime-checkable payload type.
- The only accepted absence form is `OptionalToolContext[T]`; `ToolContext[T] | None` is accepted only as deprecated syntax sugar.
- `ToolContext[A | B]`, `ToolContext[A] | B`, and `OptionalToolContext[A | B]` are invalid Context declarations.
- Ordinary non-Context unions remain outside this plan and continue through existing model-input handling.

## Compatibility Intent
- This is a deliberate breaking upgrade.
- Existing Context subclasses are unsupported after the change.
- The public annotation surface becomes `ToolContext[T]` and `OptionalToolContext[T]`.
- Direct Python calls to decorated tools must omit optional Context values successfully and receive `None`.

## Functional Boundary
- Requested Functionality: Introduce explicit Context annotation wrappers, registration-time validation, normalized Context contracts, and uniform optional Context invocation semantics.
- Protected Functionality: Context remains invisible to tool schemas, metadata, model messages, and default event input; normal model inputs retain current validation behavior.
- Explicit Non-Goals: Legacy inheritance support, DI containers, plugin systems, automatic Context construction, cross-turn retention, and unrelated tool refactors.
- Compatibility Guarantees: Breaking changes are limited to the old Context declaration contract and documented direct-call semantics for optional Context.
- Mandatory Stop Condition: Stop if implementation requires preserving Context subclass compatibility, exposing Context values to the model, or changing ordinary model-input union semantics.

## Preserved Contracts
- `Agent.run()` and `Agent.stream()` continue to accept host values by Context parameter name.
- Unknown Context names still fail before a tool invocation starts.
- Tool failures do not expose concrete Context values.
- Required Context remains required on every invocation path.

## Explicitly Permitted Contract Changes
- `ToolContext` ceases to be an inheritance marker and becomes annotation-only syntax.
- `OptionalToolContext` becomes a new public API.
- Invalid Context unions fail during `@tool` registration.
- Optional Context omission injects `None` for runtime and direct decorated-tool calls.

## Execution Constraints
- Keep implementation localized to the public type surface, tool contract parsing, invocation binding, exports, focused tests, and necessary documentation.
- Preserve UTF-8 without BOM for all changed files.
- Use English for all Python docstrings and comments introduced by implementation.
