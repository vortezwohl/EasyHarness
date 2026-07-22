# Design: D-001-reject-empty-fixed-tuple-context

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Concept
- Canonical Name: Restricted Context Annotation Grammar
- Category: Contract validation
- Reference: Python generic alias introspection

## Intent
Reject ToolContext[tuple[()]] during tool registration instead of degrading it to a bare tuple.

## Stable Core and Variation
- Stable Core: Context accepts approved concrete classes and recursive containers.
- Variation: parameterized container forms.
- Fixed Decision: the empty fixed tuple alias is unsupported.

## Repository Evidence
- The tuple branch interprets empty get_args() as an unconstrained tuple.
- A non-empty tuple has been reproduced as accepted for the empty fixed tuple annotation.

## Compatibility Boundary
- Preserve bare, fixed-length, and variadic tuple behavior.
- Raise ValueError while decorating tuple[()].

## Pattern Decision
- GoF Decision: No pattern.
- Rationale: a stable grammar rule does not justify Strategy or Interpreter.

## External Evidence Decision
- Accepted: a tuple annotation must not silently degrade to any tuple.
- Rejected: a full typing interpreter is outside the approved grammar.

## Rationale
Recognize and reject the alias before the generic tuple branch.

## Alternatives
- Validate an empty tuple at runtime: rejected.
- Degrade to bare tuple: rejected.
- Reject every no-argument tuple: rejected.

## Functional Boundary
- Requested Functionality: reject the empty fixed tuple annotation.
- Protected Functionality: valid tuple grammar, hidden schemas, and safe failures.
- Explicit Non-Goals: coercion, Union support, and new typing forms.
- Compatibility Guarantees: valid bare, fixed, and variadic tuples remain valid.
- Mandatory Stop Condition: stop if valid tuple behavior or unapproved typing support must change.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/tools.py | annotation validation | Registration-time rejection. | Current branch accepts the alias. |
| tests/test_sdk.py | Context tests | Rejection and neighboring regression cases. | Prevent recurrence. |

## Verification Seams
- Annotation registration fails.
- Tool body does not execute.
- Neighboring tuple forms pass.

## Counterexamples
The value () can exist without requiring this restricted grammar to support its annotation.

## Anti-Patterns
- Treating every empty argument list as a bare generic.
- Expanding all typing support for one edge case.

## Rules
### MUST DO
- R-D001-001: Reject tuple[()] before schema construction and tool invocation.
- R-D001-002: Test rejection and bare, fixed, and variadic tuple regressions.
### MUST NOT DO
- R-D001-N001: Do not degrade tuple[()] to bare tuple.
- R-D001-N002: Do not defer the unsupported-annotation error until invocation.
