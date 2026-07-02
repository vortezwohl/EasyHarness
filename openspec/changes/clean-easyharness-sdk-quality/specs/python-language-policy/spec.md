## ADDED Requirements

### Requirement: EasyHarness Python documentation SHALL follow repository language policy
EasyHarness Python file headers, docstrings, and key maintenance comments MUST follow the repository default language policy and therefore remain Chinese unless a narrower technical requirement explicitly calls for English.

#### Scenario: Maintainer writes a module docstring
- **WHEN** a maintainer adds or updates a Python file header, docstring, or explanatory maintenance comment
- **THEN** that text MUST default to Chinese rather than being converted to English for style alone

#### Scenario: Cleanup proposes all-English conversion
- **WHEN** a cleanup pass encounters Chinese docstrings or comments in EasyHarness Python files
- **THEN** it MUST NOT convert them to English unless the project language rules are separately changed first

### Requirement: English strings SHALL be reserved for technical boundary cases
EasyHarness MAY retain English strings where the text is part of a model-facing prompt contract, a third-party protocol field, a standardized external interface, or a test assertion that intentionally validates English output.

#### Scenario: Tool description is visible to the model
- **WHEN** a string is constructed specifically for model-facing tool instructions or protocol interoperability
- **THEN** English MAY be used or retained if it is the most compatible representation for that boundary

#### Scenario: Internal maintenance message is not externally constrained
- **WHEN** a string is only used for internal developer understanding, validation feedback, or repository-local documentation
- **THEN** the cleanup implementation MUST prefer Chinese to stay consistent with the repository default
