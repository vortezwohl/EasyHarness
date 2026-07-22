# Task: T-001-reject-empty-tuple-context

## Metadata
- Document Type: Task
- Document ID: T-001
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-002, R-D001-N001, R-D001-N002
- Prohibited New Concepts: No typing grammar expansion or runtime coercion.

## Preconditions
- D-001 is approved and the current tuple branch reproduces the accepted alias.

## Task Intent
Reject ToolContext[tuple[()]] at registration while protecting valid tuple Context forms.

## Functional Boundary
- Requested Functionality: deterministic decoration-time failure for the empty fixed tuple.
- Protected Functionality: bare, fixed, and variadic tuples, hidden schemas, and safe failures.
- Explicit Non-Goals: support for that annotation, coercion, or new typing grammar.
- Compatibility Guarantees: only tuple[()] changes; other valid annotations remain stable.
- Mandatory Stop Condition: stop if detection changes valid tuples or needs unapproved typing categories.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/tools.py | Context annotation validation | Reject alias before generic tuple handling. | Current branch accepts it. |
| tests/test_sdk.py | Context tests | Add failure and neighboring regressions. | Existing coverage misses it. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: Context compilation and its SDK tests own the behavior.
- Scope Expansion Decision Rule: expand only when an existing helper or public import must change to protect valid tuples.
- Required Assessment and Record: record paths, reason, valid-tuple impact, and verification.

## MUST DO
- M-T001-001: Implement R-D001-001 registration-time rejection.
- M-T001-002: Implement R-D001-002 regression coverage.

## MUST NOT DO
- N-T001-001: Do not violate R-D001-N001 by degrading to bare tuple.
- N-T001-002: Do not violate R-D001-N002 by failing only during invocation.

## Atomic Steps
1. Reproduce the accepted path and locate bare tuple recognition.
2. Add the minimal registration-time rejection.
3. Add failure, non-execution, and neighboring tuple tests.
4. Run focused SDK tests.

## Functional Boundary Conflict Protocol
- Escalation Trigger: distinguishing the alias requires unapproved typing aliases.
- Required Conflict Analysis: compare native-only rejection, expanded aliases, and retaining degradation with compatibility effects.
- Recommended Option: `1`
- Recommendation Rationale: native-only rejection matches the approved minimum grammar.
- Decision Prompt: Reply `1` for native-only rejection, `2` to approve expanded aliases, or `3` to stop and preserve current behavior.
- Decision Limit: this covers only empty fixed tuple recognition.
- Required Decision Record: record the choice, aliases, scope, compatibility impact, and tests.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Reject native tuple[()] only. | Completes request. | Preserves grammar. | Only one form changes. | Failure and tuple regressions. |
| 2 | Reject analyzed aliases too. | Covers more forms. | May affect unknown typing use. | Requires approval. | Alias registration tests. |
| 3 | Stop and retain behavior. | Does not complete request. | No change. | No change. | Confirm no code changes. |

## Required Verification Evidence
- Verification Procedure: run added registration tests and SDK tests.
- Required Evidence: annotation fails, tool body does not run, neighbors succeed.

## Completion Criteria
The empty fixed tuple fails at registration and protected tuple behavior passes.
