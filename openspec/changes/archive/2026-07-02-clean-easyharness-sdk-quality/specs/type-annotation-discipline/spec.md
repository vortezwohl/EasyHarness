## ADDED Requirements

### Requirement: Core EasyHarness code SHALL improve type precision where straightforward
The EasyHarness cleanup MUST tighten inaccurate or overly broad type annotations in core SDK code when the correct type can be expressed directly without introducing disproportionate abstraction or complexity.

#### Scenario: Type ignore masks a local mismatch
- **WHEN** a `type: ignore` is present because local code chose a broader type than the actual accepted values
- **THEN** the cleanup implementation MUST prefer refining the annotation or helper signature over leaving the ignore in place, unless the mismatch is imposed by a third-party dynamic boundary

#### Scenario: Any is used at a dynamic integration boundary
- **WHEN** a parameter or field sits at a genuinely dynamic framework boundary where precise typing would be misleading or high-cost
- **THEN** the cleanup implementation MAY retain `Any`, but only for that boundary rather than as a default choice throughout surrounding code

### Requirement: Public and override-facing methods SHALL not remain casually untyped
Methods that are public, participate in overrides, or define important test doubles MUST carry sufficiently precise annotations so that editors and static tooling can reason about their signatures.

#### Scenario: Test double implements framework model interface
- **WHEN** a test helper class implements a public framework interface used by EasyHarness runtime tests
- **THEN** its key methods MUST provide explicit parameter and return annotations aligned closely enough with the interface to avoid avoidable editor ambiguity

#### Scenario: Internal helper is private and trivial
- **WHEN** a private helper has a simple, local contract
- **THEN** its annotation level MAY stay pragmatic, but it MUST still avoid obvious omissions that trigger noisy editor warnings without benefit

### Requirement: Remaining type looseness SHALL be intentional and bounded
After cleanup, any retained weak typing, missing annotation, or editor type warning MUST correspond to an understood compatibility or complexity trade-off rather than accidental omission.

#### Scenario: Cleanup leaves a weakly typed boundary in place
- **WHEN** the implementation decides not to fully type a dynamic edge
- **THEN** the retained looseness MUST be limited to the smallest practical boundary and MUST NOT leak broadly into adjacent code
