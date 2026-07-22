# Subdesign: D-001-context-declaration-and-specification

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Concept
- Canonical Name: Context Parameter Specification
- Category: Direct contract model; no GoF pattern selected
- Reference: Python Annotated metadata and an immutable specification object

## Intent
Compile every recognized Context annotation into one reusable specification shared by registration, schema generation, direct calls, Agent injection, defaults, and conflict checks.

## Stable Core and Variation
- Stable core: a parameter is model-visible input or host-injected Context.
- Variation: payload annotation, optionality, source default, parameter kind, declaration order, and legacy optional syntax.

## Repository Evidence
- Current ToolContext metadata lives in easyharness/_internal/types.py.
- Current _ToolContextParameter lacks source-default and kind data.
- Agent currently compares same-name optionality as part of conflict detection.

## Compatibility Boundary
- Preserve ToolContext[T], OptionalToolContext[T], hidden schema behavior, and ToolContext[T] | None with a DeprecationWarning.
- Keep inheritance unsupported; reject positional-only parameters, Context-before-ordinary declarations, and payload unions.

## Pattern Decision
- Candidate: No GoF pattern.
- Category: Direct design.
- The fixed parsing lifecycle has no independently replaceable algorithm or object collaboration seam; Strategy, Template Method, Adapter, and Facade add unjustified indirection.

## External Evidence Decision
- Accept Annotated metadata and explicit runtime interpretation of parameterized typing forms.
- Reject a DI container, Service Locator, singleton, registry, or static-plugin architecture because invocation is already bounded.

## Rationale
Store normalized payload, optionality, source-default presence/value, parameter kind, and legacy-optional state in one immutable internal specification compiled during tool construction.

## Alternatives
- Separate direct and stream parsers: rejected because defaults and failures drift.
- Public ContextSpec: rejected because ToolContext[T] is the approved public syntax.
- Defaults alone for optionality: rejected because host injection and schema hiding become ambiguous.

## Functional Boundary
- Target: complete declaration and default semantics at registration.
- Protect: schema hiding, public annotations, private invocation maps, and ordinary inputs.
- Non-goals: broad typing support, global state, and inheritance restoration.
- Stop if this requires Context visibility, a new dependency, or ordinary-parameter contract changes.

## Code Impact Scope
- easyharness/_internal/types.py
- easyharness/_internal/tools.py
- easyharness/_internal/runtime.py
- tests/test_sdk.py

## Verification Seams
- Required/optional parsing, source-default capture, legacy warning, payload normalization, and registration-time kind/order rejection.

## Counterexamples
- ToolContext[RequestContext | OtherContext]
- ToolContext[list[RequestContext | OtherContext]]
- OptionalToolContext[RequestContext] | None

## Anti-Patterns
- Multiple Context parsers, optionality-as-type-conflict, global Context state, and model-visible Context metadata.

## Rules
### MUST DO
- R-D001-001: Compile one immutable Context specification per recognized parameter.
- R-D001-002: Preserve inspect.Parameter.empty separately from None and validate declaration order and kind at registration.
- R-D001-003: Compare same-name Agent contracts by normalized payload only.

### MUST NOT DO
- R-D001-N001: Do not restore ToolContext inheritance or add a public specification API.
- R-D001-N002: Do not add a registry, singleton, or global Context container.
