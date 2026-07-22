# Design: D-003-restore-ruff-quality-gate

## Metadata
- Document Type: Design
- Document ID: D-003
- Plan Name: tool-context-contract-hardening
- Created At: 2026-07-22:21:05:05.882
- Document Language: en-us

## Concept
- Canonical Name: Configuration-Conformant Quality Gate
- Category: Build hygiene
- Reference: Repository-local Ruff configuration

## Intent
Make ruff check easyharness tests fully pass without changing its configured rules.

## Stable Core and Variation
- Stable Core: existing Ruff rules, line length, and source/test scope.
- Variation: reported imports, line lengths, and expressions.
- Fixed Decision: repair code, not the gate.

## Repository Evidence
- pyproject.toml configures Ruff.
- The current check reports import ordering and line-length violations.

## Compatibility Boundary
- Do not change rules, line length, ignore, exclude, or dependencies.
- Do not use noqa or unrelated refactoring.

## Pattern Decision
- GoF Decision: No pattern.
- Rationale: this restores an existing quality contract.

## External Evidence Decision
- Accepted: repository Ruff configuration is the governing quality evidence.
- Rejected: generic style advice cannot replace local configuration.

## Rationale
A full clean lint result is a reliable gate; partial repair and suppression are not.

## Alternatives
- Change configuration: rejected.
- Repair only new lines: rejected.
- Add suppression: rejected.

## Functional Boundary
- Requested Functionality: clean ruff check easyharness tests.
- Protected Functionality: behavior, test meaning, dependencies, public API, and Ruff rules.
- Explicit Non-Goals: a formatter, dependency upgrades, business refactors, and rule relaxation.
- Compatibility Guarantees: only minimal behavior-neutral expression edits are allowed.
- Mandatory Stop Condition: stop if a lint repair requires changed API, test semantics, or configuration.

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness and tests | Ruff-reported lines | Minimal import and format repairs. | Full gate is required. |
| pyproject.toml | Ruff configuration | Read and protect only. | Rules must not change. |

## Verification Seams
- Ruff succeeds.
- git diff check succeeds.
- SDK tests still succeed.

## Counterexamples
Runnable code is not proof that lint passes; configuration changes are not repairs.

## Anti-Patterns
- Hiding violations with noqa.
- Refactoring business logic for line length.

## Rules
### MUST DO
- R-D003-001: Repair each full Ruff report minimally until the command is clean.
- R-D003-002: Run SDK tests and git diff check after edits.
### MUST NOT DO
- R-D003-N001: Do not change Ruff rules, line length, ignore, or exclude.
- R-D003-N002: Do not use noqa, dependency changes, or unrelated refactors.
