# sdk-code-hygiene Specification

## Purpose
TBD - created by archiving change clean-easyharness-sdk-quality. Update Purpose after archive.
## Requirements
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

### Requirement: Static methods SHALL only be introduced when semantically safe
The cleanup process MUST NOT mechanically convert every method that does not currently read `self` or `cls` into a static method. A method MAY be converted to `@staticmethod` only when it does not participate in instance protocol, abstract base class, override, property, or `Protocol` semantics.

#### Scenario: Helper method does not use instance state
- **WHEN** a private helper method does not use instance state and is not part of an inherited or protocol-defined instance API
- **THEN** the cleanup implementation MAY convert it to a static method if doing so improves clarity

#### Scenario: Method belongs to a protocol or override chain
- **WHEN** a method currently does not use `self` but exists to satisfy a `Protocol`, abstract method, property, or override contract
- **THEN** the cleanup implementation MUST preserve instance-method semantics and MUST NOT staticize it solely to silence a warning

### Requirement: Editor warnings SHALL be reduced to intentional exceptions
The EasyHarness cleanup MUST aim for a warning baseline where remaining editor warnings are intentional, limited, and explainable, rather than accidental leftovers from rushed implementation.

#### Scenario: Warning is emitted by local code
- **WHEN** PyCharm-like inspections or equivalent static tools highlight a warning in EasyHarness-owned code
- **THEN** the cleanup implementation MUST either remove the cause or keep it only when the warning is tied to a deliberate interface constraint or dynamic boundary

#### Scenario: Warning is intentionally kept
- **WHEN** a warning cannot be cleanly removed without harming readability, compatibility, or protocol correctness
- **THEN** the implementation MUST retain it only with a clear rationale embodied in the code structure or surrounding type choices rather than by silent neglect

