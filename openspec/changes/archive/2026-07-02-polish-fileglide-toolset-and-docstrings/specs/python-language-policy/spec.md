## MODIFIED Requirements

### Requirement: EasyHarness Python documentation SHALL follow repository language policy
EasyHarness Python file headers, docstrings, and key maintenance comments MUST follow the repository language policy and therefore default to en-us across `easyharness/`, unless a narrower external contract requires another language inside the affected code surface.

#### Scenario: Maintainer writes a module docstring
- **WHEN** a maintainer adds or updates a Python file header, docstring, or explanatory maintenance comment in `easyharness/`
- **THEN** that text MUST default to en-us rather than Chinese

#### Scenario: Cleanup encounters legacy Chinese documentation
- **WHEN** a cleanup pass encounters Chinese docstrings or comments in EasyHarness Python files
- **THEN** it MUST convert those maintenance texts to en-us as part of bringing the code back into policy compliance

### Requirement: English strings SHALL be reserved for technical boundary cases
The en-us documentation rule applies directly to maintainer-facing Python comments and docstrings. Model-facing prompts, protocol field names, structured runtime payloads, and test assertions MUST keep the language required by their external interface or validation contract, and MUST NOT be rewritten solely for documentation-style consistency.

#### Scenario: Tool description is visible to the model
- **WHEN** a string is constructed specifically for model-facing tool instructions or protocol interoperability
- **THEN** the implementation MAY keep or convert that boundary string according to the tool contract, rather than because Python documentation now defaults to en-us

#### Scenario: Internal maintenance text is not externally constrained
- **WHEN** a string exists only for internal maintainer understanding as a Python file header, docstring, or explanatory maintenance comment
- **THEN** the codebase MUST prefer en-us so that EasyHarness maintenance documentation stays consistent
