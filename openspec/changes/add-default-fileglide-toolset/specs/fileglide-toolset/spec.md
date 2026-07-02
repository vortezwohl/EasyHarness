## ADDED Requirements

### Requirement: SDK MUST expose the official fileglide toolset from `easyharness.toolset`
The SDK MUST expose the official fileglide-based toolset through the `easyharness.toolset` package. The package MUST provide a public `build_fileglide_tools` entry point for constructing the official file tool collection. The root `easyharness` package MUST NOT re-export that builder or the toolset package as a top-level public SDK name.

#### Scenario: Developer imports the official toolset
- **WHEN** a developer imports `build_fileglide_tools` from `easyharness.toolset`
- **THEN** the SDK MUST provide a supported builder for the official fileglide tool collection

#### Scenario: Root package public names remain minimal
- **WHEN** a developer inspects `easyharness.__all__`
- **THEN** the top-level public SDK names MUST remain limited to `Agent`, `ModelConfig`, `AgentEvent`, `ToolOutput`, and `tool`

### Requirement: Official fileglide toolset MUST provide a curated default coding-agent collection
`build_fileglide_tools()` MUST return a curated official tool collection intended for coding-agent use rather than a one-to-one export of every fileglide CLI command. The default collection MUST include stable tools for tree listing, path search, text reading, text search, text editing, path management, and path inspection.

#### Scenario: Default builder returns the official curated tool set
- **WHEN** a developer calls `build_fileglide_tools()` with default arguments
- **THEN** the returned collection MUST include the official tools `fs_list_tree`, `fs_search_paths`, `fs_read_text`, `fs_search_text`, `fs_edit_text`, `fs_manage_paths`, and `fs_inspect_path`

#### Scenario: Default builder excludes raw command-tree exposure
- **WHEN** a developer uses the default official fileglide toolset
- **THEN** the collection MUST expose the curated official tool names rather than the full underlying fileglide command tree

### Requirement: Official fileglide toolset MUST support scoped construction
`build_fileglide_tools` MUST allow the caller to construct the official toolset for an explicit filesystem root. Tools created from that builder MUST execute against the configured root scope and rely on fileglide scope enforcement for path escape protection.

#### Scenario: Developer builds tools for an explicit root
- **WHEN** a developer calls `build_fileglide_tools(root="D:/Projects/PythonProjects/EasyHarness")`
- **THEN** the returned tools MUST execute fileglide operations using that root as their scope

#### Scenario: Scoped tools reject escaped targets
- **WHEN** a scoped official tool receives a target that escapes the configured root
- **THEN** the tool MUST report a structured scope failure rather than silently operating outside the configured root

### Requirement: Official fileglide tools MUST normalize outputs and failures for EasyHarness
Official fileglide tools MUST adapt fileglide results and domain failures into EasyHarness-compatible structured outputs. Successful tool results MUST be JSON-serializable for `ToolOutput.data`, and fileglide failures MUST preserve structured error information instead of leaking raw dataclass objects or unnormalized exception payloads.

#### Scenario: Successful fileglide result is JSON-safe
- **WHEN** an official fileglide tool returns a result that includes fileglide dataclass values such as preview metadata
- **THEN** the tool MUST normalize the payload into JSON-serializable primitives before exposing it through the EasyHarness tool contract

#### Scenario: Fileglide domain failure remains structured
- **WHEN** an official fileglide tool encounters a fileglide validation, scope, encoding, or not-found error
- **THEN** the tool MUST expose a structured error payload that preserves the error code, message, details, and path for model and UI consumption
