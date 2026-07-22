# Subdesign: D-002-unified-invocation-semantics

## Metadata
- Document Type: Design
- Document ID: D-002
- Plan Name: tool-context-contract-redesign
- Created At: 2026-07-22:16:05:19.279
- Document Language: en-us

## Concept
- Canonical Name: Normalized Context Invocation Contract
- Category: Invocation Binding Policy
- Reference: Existing EasyHarness invocation state and decorated-tool call paths.

## Intent
Use the same normalized Context contract for tool registration, agent runtime injection, and direct calls to decorated tool objects.

## Stable Core and Variation
- Stable core: each Context contract provides a parameter name, one payload type, and an optional flag.
- Variation: invocation arrives through agent runtime state or direct Python arguments, but both paths apply the same optionality and type rules.

## Repository Evidence
- `_resolve_context_arguments()` currently validates runtime injection but allows omission only when the original function already has a default.
- `_EasyHarnessTool.__call__()` currently forwards arguments without Context resolution.
- `Agent.run()` and `Agent.stream()` both construct per-invocation state by parameter name.

## Compatibility Boundary
- Optional Context omission must inject `None` for both agent and direct decorated-tool calls.
- Required Context remains required.
- This intentional direct-call semantic change is part of the breaking upgrade.

## Pattern Decision
- Decision: Use a direct shared contract and reject GoF patterns.
- Why: the implementation needs one source of truth, not an extensible algorithm hierarchy.
- Rejected neighbors: Template Method would introduce unnecessary inheritance for two simple binding paths; Facade would not solve the consistency requirement.

## External Evidence Decision
- Accepted evidence: a public wrapper must expose call semantics that match its effective behavior.
- Accepted evidence: default injection belongs at the common contract boundary so every supported invocation path agrees.
- Rejected evidence: runtime-only optional injection would retain the current split between agent execution and direct calls.

## Rationale
The decorated tool object must bind supplied arguments, add `None` for each omitted optional Context parameter, verify explicit Context values against the normalized payload type, and invoke the original function. Runtime resolution uses the same contract and injects `None` when an optional Context name is absent. The decorated tool exposes a signature where optional Context parameters visibly default to `None`.

## Alternatives
- Change only runtime Context resolution: rejected because direct decorated-tool calls would remain inconsistent.
- Mutate the original function implementation or its code object: rejected because it obscures debugging and changes user-owned function behavior.

## Functional Boundary
- Target functionality: make optional Context omission equivalent to an injected `None` in every supported invocation path.
- Protected related functionality: required Context failures, unknown Context name checks, error redaction, and normal parameter behavior remain stable.
- Explicit non-goals: validation changes for normal model inputs, automatic Context factories, and cross-turn Context persistence.
- Hard-stop condition: stop if a consistent implementation requires changing the Strands protocol or retaining separate direct-call and runtime Context rules.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/tools.py` | `_resolve_context_arguments` and `__call__` | Share normalized binding logic, inject optional `None`, and expose accurate call signature. | Current runtime and direct-call behavior diverge here. |
| `easyharness/_internal/runtime.py` | Invocation contracts and state | Keep name validation while providing the normalized Context mapping to tools. | Runtime owns per-turn Context state. |
| `tests/test_sdk.py` | Runtime and direct-call coverage | Assert optional omission, required failures, wrong types, and no data leakage. | Existing tests cover only part of the invocation behavior. |

## Verification Seams
- Missing optional Context resolves to `None` in `Agent.run()` and `Agent.stream()`.
- Missing optional Context resolves to `None` during direct decorated-tool calls.
- Missing required Context fails at the wrapper boundary with stable diagnostics.
- Explicit wrong Context types fail without leaking the supplied object value.
- `inspect.signature()` matches the decorated tool's direct-call semantics.

## Counterexamples
- A tool that needs a derived default object should receive `None` and derive it in the function body; the SDK must not guess or construct domain values.
- A caller that wants direct and runtime behavior to differ is outside the approved boundary.

## Anti-Patterns
- Keeping `__call__()` as a bare passthrough while runtime injection gains new rules.
- Making optional behavior depend on whether a tool author manually wrote `= None` in the original signature.
- Retaining Context state after an agent turn ends.

## Rules
### MUST DO
- R-D002-001: Reuse normalized Context contracts for schema generation, runtime injection, and direct decorated-tool binding.
- R-D002-002: Inject `None` whenever an optional Context parameter is omitted from a supported invocation path.
- R-D002-003: Preserve required Context failures and unknown Context name validation.
- R-D002-004: Make decorated-tool introspection reflect optional Context default semantics.

### MUST NOT DO
- R-D002-N001: Do not keep different optional Context rules for direct and agent calls.
- R-D002-N002: Do not modify user function code objects or create hidden default Context instances.
- R-D002-N003: Do not retain Context values beyond a single agent invocation.
- R-D002-N004: Do not broaden normal parameter runtime type checking.
