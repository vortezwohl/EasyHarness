# Subdesign: D-003-unified-binding-and-agent-contracts

## Metadata
- Document Type: Design
- Document ID: D-003
- Plan Name: tool-context-deep-contract
- Created At: 2026-07-22:18:12:52.218
- Document Language: en-us

## Concept
- Canonical Name: Unified Context Binding Lifecycle
- Category: Direct invocation lifecycle; no GoF pattern selected
- Reference: Python signature binding and existing per-invocation state

## Intent
Make direct decorated-tool calls and Agent calls apply identical explicit-value, source-default, optional-None, required-failure, and payload-validation rules.

## Stable Core and Variation
- Stable core: ordinary functions are wrapped; Agent owns one private map per invocation; final calls use keywords.
- Variation: direct versus Agent entry, value presence, source defaults, and required/optional declaration.

## Repository Evidence
- Direct calls bind the raw signature today; stream calls use keyword merging; missing optional values ignore source defaults; Agent rejects same-name mixed optionality.

## Compatibility Boundary
- Explicit value wins, then source default, then optional None fallback; required absence fails only when selected.
- Unknown Context names remain entry failures; positional-only and front-position Context declarations fail at registration.

## Pattern Decision
- Candidate: No GoF pattern.
- Category: Direct lifecycle design.
- Facade, Command, Chain of Responsibility, and Proxy do not match this shared binding seam.

## External Evidence Decision
- Accept explicit runtime boundary validation; reject monkey-patching signatures, a default-value DSL, and mandatory required-Context checks at Agent entry.

## Rationale
Project a direct-call signature preserving source defaults and showing None only for optional Context without a default. Bind through that projection, resolve Context centrally, then keyword-call the original function. Agent compares normalized same-name payloads only.

## Alternatives
- Require all Context at Agent entry: rejected because selected tools are model-dependent.
- Keep optionality in conflicts: rejected by the approved contract.
- Let defaults bypass resolver: rejected because stream validation and safe errors must remain identical.

## Functional Boundary
- Target: identical Context semantics across direct and Agent paths.
- Protect: schema hiding, unknown-name errors, map isolation, safe failures, and non-Context validation.
- Non-goals: session persistence, automatic Context construction, *args, **kwargs, and model-selection changes.
- Stop if unification changes ordinary parameter behavior or Context visibility.

## Code Impact Scope
- easyharness/_internal/tools.py
- easyharness/_internal/runtime.py
- tests/test_sdk.py
- tests/旧版本教程.md

## Verification Seams
- Defaults on both paths, optional omission after ordinary arguments, mixed optionality, payload mismatch, missing required safe failure, and concurrent map isolation.

## Counterexamples
- Context before an ordinary positional-or-keyword parameter.
- Any positional-only tool parameter.
- Same-name Context declarations with different payloads.

## Anti-Patterns
- Separate direct and Agent resolvers, optionality-as-type-conflict, Agent-global Context state, and late positional-only failure.

## Rules
### MUST DO
- R-D003-001: Route direct and Agent paths through one Context resolver.
- R-D003-002: Apply explicit value, source default, optional None, and required failure in that order.
- R-D003-003: Keep one private Context map per invocation and compare same-name payloads only.

### MUST NOT DO
- R-D003-N001: Do not drop source defaults or expose Context in schemas or event inputs.
- R-D003-N002: Do not permit positional-only parameters, *args, **kwargs, or Context stored on Agent instances/globals.
