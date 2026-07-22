# Task: T-003-restore-ruff-gate

## Metadata
- Document Type: Task
- Document ID: T-003
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Design Sources
- Source Design References: D-003
- Design Rule References: R-D003-001, R-D003-002, R-D003-N001, R-D003-N002
- Prohibited New Concepts: No Ruff configuration change, suppression, dependency change, or unrelated refactor.

## Preconditions
- D-003 is approved and the configured Ruff executable is available.

## Task Intent
Make ruff check easyharness tests pass without configuration or suppression changes.

## Functional Boundary
- Requested Functionality: repair every reported import, line, and expression violation.
- Protected Functionality: behavior, tests, dependencies, API, and Ruff rules.
- Explicit Non-Goals: configuration edits, noqa, unrelated formatting, and business refactors.
- Compatibility Guarantees: only minimal behavior-neutral edits are allowed.
- Mandatory Stop Condition: stop if a repair needs changed API, test semantics, or configuration.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness and tests | Ruff-reported lines | Minimal import and formatting repairs. | Full gate is required. |
| pyproject.toml | Ruff config | Read and protect only. | Rules must remain stable. |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: Ruff output defines the source and test surface.
- Scope Expansion Decision Rule: change only reported files; escalate behavior changes.
- Required Assessment and Record: record initial and final output, files, and regression evidence.

## MUST DO
- M-T003-001: Implement R-D003-001 until full Ruff output is clean.
- M-T003-002: Implement R-D003-002 with SDK and diff checks.

## MUST NOT DO
- N-T003-001: Do not violate R-D003-N001 by changing rules, line length, ignore, or exclude.
- N-T003-N002: Do not violate R-D003-N002 with noqa, dependency changes, or unrelated refactors.

## Atomic Steps
1. Record the complete Ruff report by file.
2. Repair each report minimally without behavior changes.
3. Re-run Ruff until clean.
4. Run SDK and diff checks.

## Functional Boundary Conflict Protocol
- Escalation Trigger: a lint violation cannot be fixed without changing protected behavior or rules.
- Required Conflict Analysis: compare minimal rewrite, rule relaxation, and retaining the error.
- Recommended Option: `1`
- Recommendation Rationale: minimal rewrites preserve the approved quality gate.
- Decision Prompt: Reply `1` for a minimal behavior-neutral rewrite, `2` to approve a rule change, or `3` to stop and retain the error.
- Decision Limit: this covers only the blocked rule and file.
- Required Decision Record: record the rule, file, alternatives, choice, impact, and verification.

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Minimal behavior-neutral rewrite. | Restores Ruff. | Preserves behavior and rules. | No external change. | Ruff, SDK, diff. |
| 2 | Change a stated rule. | May pass lint. | Changes quality contract. | Requires approval. | Config and lint verification. |
| 3 | Stop and retain error. | Does not complete request. | No change. | Gate remains failing. | Confirm no repair. |

## Required Verification Evidence
- Verification Procedure: run Ruff, SDK tests, and git diff check.
- Required Evidence: Ruff and diff succeed, SDK succeeds, and no config or suppression changes exist.

## Completion Criteria
Ruff is clean and SDK plus diff checks pass.
