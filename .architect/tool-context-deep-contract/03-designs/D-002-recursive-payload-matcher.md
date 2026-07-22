# Subdesign: D-002-recursive-payload-matcher

## Metadata
- Document Type: Design
- Document ID: D-002
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Concept
- Canonical Name: Recursive Runtime Type Matching
- Category: Direct recursive interpreter; no GoF Interpreter pattern selected
- Reference: Python get_origin/get_args runtime typing interpretation

## Intent
Validate Context payloads deeply and without coercion for approved classes, scalars, and dict/list/tuple/set containers.

## Stable Core and Variation
- Stable core: matching is boolean, side-effect-free, identity-preserving, and redacted.
- Variation: scalar classes, parent classes, bare/parameterized containers, tuple forms, and nesting.

## Repository Evidence
- Current validation is class-only isinstance in direct and stream paths.
- Existing safe-failure tests require no secret Context contents.

## Compatibility Boundary
- Support concrete classes, ABC parents, scalar runtime classes, and dict/list/tuple/set recursively.
- Accept subclass values for a parent class; allow explicit None only for ToolContext[object] with a migration prompt.
- Reject Any, NoneType, Protocol, unions, Callable, Literal, TypeVar, TypedDict, Mapping, and Sequence.

## Pattern Decision
- Candidate: No GoF pattern.
- Category: Direct design.
- The closed annotation grammar maps to a boolean result; Interpreter, Composite, Visitor, and Strategy add extension machinery without a real extension lifecycle.

## External Evidence Decision
- Accept explicit recursive generic handling; reject Pydantic coercion and a matcher plugin registry to preserve Context identity and a closed grammar.

## Rationale
Use one recursive helper: classes use isinstance; dict/list/set validate all members; fixed tuples validate arity and positions; tuple[T, ...] validates every member; active pairs prevent cyclic-container recursion.

## Alternatives
- Shallow checks: rejected by the approved deep-validation choice.
- TypeAdapter coercion: rejected because it can alter host objects.
- Dataclass-only support: rejected because scalar and container Context payloads are approved.

## Functional Boundary
- Target: deep payload validation with parent compatibility and safe failures.
- Protect: identity, redaction, schema hiding, and map isolation.
- Non-goals: arbitrary typing forms, structural protocols, coercion, serialization, and caching.
- Stop if deep validation cannot preserve identity or redaction.

## Code Impact Scope
- easyharness/_internal/tools.py
- tests/test_sdk.py

## Verification Seams
- Valid/invalid nested dict/list/tuple/set, empty containers, tuple variants, subclass values, object None warning, and rejected annotations.

## Counterexamples
- ToolContext[dict[str, int]] with a string value.
- ToolContext[list[BaseContext]] with an unrelated element.
- ToolContext[tuple[str, int]] with wrong arity.

## Anti-Patterns
- isinstance against parameterized generics, value coercion, repr(value) errors, and Protocol treated as nominal inheritance.

## Rules
### MUST DO
- R-D002-001: Use one recursive no-coercion matcher for every direct and stream payload check.
- R-D002-002: Deeply validate all declared dict/list/tuple/set members while preserving class-subclass compatibility.
- R-D002-003: Redact raw payload values from all errors and events.

### MUST NOT DO
- R-D002-N001: Do not accept payload unions, Any, Protocol, or unsupported typing forms.
- R-D002-N002: Do not copy, serialize, cache, freeze, or mutate a Context payload.
