# Subdesign: D-001-context-annotation-surface

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Concept
- Canonical Name: Annotation-Metadata Context Contract
- Category: Public SDK Type Contract
- Reference: Explicit type metadata and optionality semantics adapted to the existing EasyHarness tool contract.

## Intent
Replace subclass-based Context recognition with annotation syntax that identifies one concrete host-provided payload type per Context parameter.

## Stable Core and Variation
- Stable core: Context is host-provided, private to the tool invocation, and excluded from model input.
- Variation: a Context parameter is required or optional, while its payload type remains a single runtime-checkable type.

## Repository Evidence
- `_tool_context_annotation()` currently uses subclass checks and limited union inspection.
- `_build_input_model()` excludes only parameters already recognized as Context.
- The public package exports `ToolContext` as a base class marker.

## Compatibility Boundary
- Breaking upgrade: subclassing `ToolContext` is unsupported.
- Public declarations are `ToolContext[T]` and `OptionalToolContext[T]`.
- `ToolContext[T] | None` is parsed as deprecated optional syntax; no other Context union is accepted.

## Pattern Decision
- Decision: Use a direct annotation-contract design and reject GoF patterns.
- Why: the seam is type-contract parsing, not a variable object collaboration algorithm.
- Rejected neighbors: Adapter would preserve a compatibility layer that is explicitly out of scope; Strategy would add interchangeable parsing policies without a real variation family.

## External Evidence Decision
- Accepted evidence: explicit metadata attached to a type declaration is a better fit than forcing domain classes into an SDK inheritance hierarchy.
- Accepted evidence: optionality represents absence and must not be used to widen Context payload types to multiple business alternatives.
- Rejected evidence: generalized union acceptance is unsuitable because it makes schema hiding and runtime type validation ambiguous.

## Rationale
`ToolContext[T]` and `OptionalToolContext[T]` make host injection visible in the signature without coupling `T` to an SDK base type. Registration normalizes both forms into one internal Context contract. A payload type must be a single runtime-checkable type. Context unions containing two concrete payload alternatives fail before the tool becomes available.

## Alternatives
- Keep subclass recognition and add one invalid-union branch: rejected because inheritance remains coupled to business modeling and optionality remains indirect.
- Expose raw `Annotated` metadata without public wrappers: rejected because it leaks implementation details and weakens the public API.

## Functional Boundary
- Target functionality: provide explicit required and optional Context annotation forms and reject ambiguous Context unions at registration.
- Protected related functionality: Context parameters remain absent from schemas, metadata, model messages, and default event input.
- Explicit non-goals: legacy subclass compatibility, automatic Context creation, dependency containers, and changes to normal model-input unions.
- Hard-stop condition: stop if implementation requires a legacy inheritance parser or makes a Context parameter visible to model input.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/types.py` | Public Context marker surface | Replace inheritance marker with annotation-only wrappers and internal metadata. | Current public `ToolContext` type lives here. |
| `easyharness/_internal/tools.py` | Type-hint and Context parsing | Preserve annotation metadata, normalize Context declarations, and reject invalid unions. | Current recognition and schema exclusion live here. |
| `easyharness/__init__.py` | Public exports | Export `OptionalToolContext` and the redesigned `ToolContext`. | Current public exports are centralized here. |
| `tests/test_sdk.py` | Tool contract tests | Replace subclass fixtures and add registration contract coverage. | Existing Context behavior is covered here. |

## Verification Seams
- Tool registration accepts `ToolContext[T]` and `OptionalToolContext[T]`.
- Tool registration rejects Context declarations with more than one concrete payload type.
- Context parameters remain absent from tool schema and metadata validation.
- Context payload type checks remain safe and do not render concrete values in failure text.

## Counterexamples
- A tool that truly supports multiple host implementations must use one shared runtime-checkable base type or protocol as `T`, not a union.
- A model-provided parameter must remain a normal parameter even if its name resembles a request or session object.

## Anti-Patterns
- Supporting subclass and annotation parsing as equal long-term authorities.
- Treating every union that contains a Context form as a valid polymorphic injection contract.
- Adding a global Context registry to solve a declaration problem.

## Rules
### MUST DO
- R-D001-001: Define public required and optional Context annotation wrappers without requiring payload types to inherit an SDK base class.
- R-D001-002: Normalize every accepted Context declaration into one internal contract with parameter name, payload type, and optionality.
- R-D001-003: Reject an invalid Context union during `@tool` registration with an actionable error.
- R-D001-004: Exclude every normalized Context parameter from model input schema and metadata parameter matching.

### MUST NOT DO
- R-D001-N001: Do not retain Context subclass compatibility or a second legacy recognition path.
- R-D001-N002: Do not accept a Context payload union with multiple concrete types.
- R-D001-N003: Do not alter ordinary non-Context union processing.
- R-D001-N004: Do not expose Context values or Context parameter descriptions to the model.
