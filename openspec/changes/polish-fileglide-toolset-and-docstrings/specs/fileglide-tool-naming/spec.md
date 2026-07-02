## ADDED Requirements

### Requirement: Official curated fileglide tools MUST use `fileglide_` public names
EasyHarness MUST expose the official curated fileglide toolset under stable `fileglide_`-prefixed public names. The curated default set MUST use `fileglide_list_tree`, `fileglide_search_paths`, `fileglide_read_text`, `fileglide_search_text`, `fileglide_edit_text`, `fileglide_manage_paths`, and `fileglide_inspect_path`.

#### Scenario: Default builder returns renamed curated tools
- **WHEN** a developer calls `build_fileglide_tools()` with default arguments
- **THEN** the returned collection MUST expose exactly the official public names `fileglide_list_tree`, `fileglide_search_paths`, `fileglide_read_text`, `fileglide_search_text`, `fileglide_edit_text`, `fileglide_manage_paths`, and `fileglide_inspect_path`

#### Scenario: Default auto-load uses the renamed override points
- **WHEN** a developer constructs `Agent(enable_file_tools=True, tools=[custom_tool])` and `custom_tool` publishes the name `fileglide_read_text`
- **THEN** the explicit tool MUST override the default renamed read tool while the agent continues to auto-load the remaining official `fileglide_*` tools

### Requirement: Legacy `fs_*` aliases MUST NOT remain part of the official tool contract
After the rename, EasyHarness MUST NOT keep a second official `fs_*` alias surface for the curated fileglide tools, because duplicate public names would expand the default tool surface and create model-facing ambiguity.

#### Scenario: Developer inspects the official tool names
- **WHEN** a developer builds the official curated fileglide toolset and inspects each `tool_name`
- **THEN** none of the official tool names MUST start with `fs_`
