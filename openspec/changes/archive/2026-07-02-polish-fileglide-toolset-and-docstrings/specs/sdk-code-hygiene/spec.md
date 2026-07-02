## MODIFIED Requirements

### Requirement: EasyHarness code SHALL remove deterministic code noise
The EasyHarness Python codebase MUST remove deterministic low-value noise from `easyharness/` and relevant tests, including unused imports, unused parameters, import-order drift, and formatter-detectable long-line/style violations when those fixes do not change runtime behavior. When static analysis flags an unused import or an unused parameter, the maintainer MUST verify whether it is truly dead, required by an interface or override contract, or evidence that the implementation has drifted away from its intended logic before deciding to remove or retain it.

#### Scenario: Unused symbols are discovered
- **WHEN** static analysis finds an unused import or an unused parameter in EasyHarness-owned code
- **THEN** the codebase MUST remove it or explicitly justify its retention through a protocol, override, or dynamic-interface requirement rather than leaving it as accidental noise

#### Scenario: Unused parameter reveals dropped behavior
- **WHEN** investigation shows that an apparently unused import or parameter exists because the current implementation no longer wires the behavior it was meant to support
- **THEN** the implementation MUST restore or correct that logic instead of silencing the warning by deletion alone

#### Scenario: Import order or formatting drifts
- **WHEN** `ruff check` or `ruff format --check` reports import-order or formatting issues in the targeted files
- **THEN** the cleanup implementation MUST normalize those files to the agreed formatting baseline without changing externally observable behavior
