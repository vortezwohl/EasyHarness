"""Official fileglide-backed filesystem tools for EasyHarness.

This module adapts fileglide services into the public EasyHarness tool
contract. The curated toolset is intended for coding agents that need stable,
out-of-the-box file browsing, search, editing, and inspection capabilities
without expanding the root package surface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from fileglide.exceptions import FileGlideError, ValidationError
from fileglide.facade import FileGlideFacade
from fileglide.serializers import to_primitive

from easyharness._internal.tools import tool
from easyharness._internal.types import ToolOutput


def _normalize_patterns(patterns: list[str] | None) -> tuple[str, ...]:
    """Return a stable tuple of non-empty include or exclude patterns."""

    return tuple(item for item in (patterns or []) if item)


def _serialize_detail(payload: object) -> str:
    """Serialize a payload into readable JSON detail text."""

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _result_summary(operation: str, payload: dict[str, Any]) -> str:
    """Build a short human-readable summary for a successful result."""

    if "count" in payload:
        return f"{operation}: {payload['count']} items"
    if "line_count" in payload:
        return f"{operation}: {payload['line_count']} lines"
    if "size_bytes" in payload:
        return f"{operation}: {payload['size_bytes']} bytes"

    entry = payload.get("entry")
    if isinstance(entry, dict) and entry.get("relative_path"):
        return f"{operation}: {entry['relative_path']}"
    return f"{operation}: ok"


def _success_output(
    *,
    operation: str,
    root: Path,
    result: dict[str, Any],
) -> ToolOutput:
    """Build the normalized EasyHarness output for a successful operation."""

    primitive_result = to_primitive(result)
    data = {
        "ok": True,
        "operation": operation,
        "root": str(root),
        "result": primitive_result,
    }
    summary = _result_summary(operation, primitive_result)
    return ToolOutput(
        data=data,
        model_text=summary,
        preview=summary,
        detail=_serialize_detail(data),
    )


def _error_output(
    *,
    operation: str,
    root: Path,
    error: FileGlideError,
) -> ToolOutput:
    """Build the normalized EasyHarness output for a fileglide failure."""

    error_payload = {
        "code": error.code,
        "message": error.message,
        "details": to_primitive(error.details),
        "path": error.path,
    }
    data = {
        "ok": False,
        "operation": operation,
        "root": str(root),
        "error": error_payload,
    }
    summary = f"{operation}: {error.code} - {error.message}"
    return ToolOutput(
        data=data,
        model_text=summary,
        preview=summary,
        detail=_serialize_detail(data),
    )


def _run_fileglide(
    *,
    root: Path,
    operation: str,
    action: Callable[[], dict[str, Any]],
) -> ToolOutput:
    """Run one fileglide action and normalize the result."""

    try:
        result = action()
    except FileGlideError as error:
        return _error_output(operation=operation, root=root, error=error)
    return _success_output(operation=operation, root=root, result=result)


def _require_text_content(action: str, content: str | None) -> str:
    """Validate the text content required by a text-editing action."""

    if content is None:
        raise ValidationError(
            code="missing_content",
            message="The selected text action requires content.",
            details={"action": action},
        )
    return content


def _validate_manage_action(action: str, kind: str) -> None:
    """Validate the requested path-management action and target kind."""

    valid_actions = {"create", "exists", "delete", "move"}
    if action not in valid_actions:
        raise ValidationError(
            code="invalid_manage_action",
            message="Action must be create, exists, delete, or move.",
            details={"action": action},
        )
    if kind not in {"file", "directory"}:
        raise ValidationError(
            code="invalid_manage_kind",
            message="Kind must be file or directory.",
            details={"kind": kind},
        )


def _validate_inspect_action(action: str) -> None:
    """Validate the requested inspection action."""

    if action not in {"size", "read_bytes"}:
        raise ValidationError(
            code="invalid_inspect_action",
            message="Action must be size or read_bytes.",
            details={"action": action},
        )


def build_fileglide_tools(root: str | Path | None = None) -> list[object]:
    """Build the official curated fileglide toolset.

    Args:
        root: Root directory enforced by the fileglide scope. The current
            working directory is used when omitted.

    Returns:
        Official tool objects ready to be passed into `Agent(tools=[...])`.
    """

    facade = FileGlideFacade()
    resolved_root = facade.scope.normalize_root(root)
    root_text = str(resolved_root)
    content_source = {"source": "easyharness.toolset"}

    @tool(
        name="fileglide_list_tree",
        purpose=(
            "List directory trees, file entries, and basic metadata inside the "
            "configured root scope."
        ),
        when_to_use=(
            "Use this when the model needs to understand the workspace "
            "structure, inspect which files exist under a directory, or build "
            "tree context before editing."
        ),
        parameters={
            "start": (
                "Traversal starting point. Relative and absolute paths are "
                "accepted, but the path must stay within the configured scope."
            ),
            "kind": "Entry type filter: all, file, or directory.",
            "recursive": "Whether to recurse into child directories.",
            "max_depth": "Maximum recursion depth, or None for no explicit cap.",
            "include": "Optional include patterns that match names or paths.",
            "exclude": "Optional exclude patterns that match names or paths.",
        },
        returns=(
            "A structured tree listing with entry metadata and a normalized "
            "JSON-safe EasyHarness result payload."
        ),
        common_failures=[
            "The starting path does not exist or escapes the configured scope.",
            "The kind argument is invalid.",
        ],
    )
    def fileglide_list_tree(
        start: str = ".",
        kind: str = "all",
        recursive: bool = False,
        max_depth: int | None = None,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> ToolOutput:
        """List the file tree and basic metadata."""

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_list_tree",
            action=lambda: facade.traversal.list_entries(
                root_text,
                start=start,
                kind=kind,
                recursive=recursive,
                max_depth=max_depth,
                include=_normalize_patterns(include),
                exclude=_normalize_patterns(exclude),
            ),
        )

    @tool(
        name="fileglide_search_paths",
        purpose=(
            "Search for files and directories by name, path fragment, or fuzzy "
            "matching inside the configured scope."
        ),
        when_to_use=(
            "Use this when the model knows an approximate file name, module "
            "name, or path fragment but does not know the exact location yet."
        ),
        parameters={
            "query": "Search text used to find matching paths.",
            "mode": "Search mode: exact, contains, or fuzzy.",
            "start": (
                "Search starting point. Relative and absolute paths are "
                "accepted, but the path must stay within the configured scope."
            ),
            "kind": "Target type filter: all, file, or directory.",
            "recursive": "Whether to recurse into child directories.",
            "max_depth": "Maximum recursion depth, or None for no explicit cap.",
            "include": "Optional include patterns.",
            "exclude": "Optional exclude patterns.",
            "limit": "Maximum number of matches to return.",
        },
        returns=(
            "A structured match list with scores and a normalized EasyHarness "
            "result payload."
        ),
        common_failures=[
            "The search mode is invalid.",
            "The starting path does not exist or escapes the configured scope.",
        ],
    )
    def fileglide_search_paths(
        query: str,
        mode: str = "contains",
        start: str = ".",
        kind: str = "all",
        recursive: bool = True,
        max_depth: int | None = None,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        limit: int = 50,
    ) -> ToolOutput:
        """Search path names and relative paths."""

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_search_paths",
            action=lambda: facade.search.search_names(
                root_text,
                query=query,
                mode=mode,
                start=start,
                kind=kind,
                recursive=recursive,
                max_depth=max_depth,
                include=_normalize_patterns(include),
                exclude=_normalize_patterns(exclude),
                limit=limit,
            ),
        )

    @tool(
        name="fileglide_read_text",
        purpose=(
            "Read the full text of a file or a selected line range inside the "
            "configured scope."
        ),
        when_to_use=(
            "Use this when the model needs source code, configuration, log, or "
            "documentation content while preserving line and encoding details."
        ),
        parameters={
            "target": "Path to the text file that should be read.",
            "start_line": "Optional first line number. Omit to start at line 1.",
            "end_line": "Optional last line number. Omit to read to the end.",
            "encoding": (
                "Optional explicit encoding. When omitted, fileglide will "
                "detect the encoding automatically."
            ),
        },
        returns=(
            "Structured text content, line metadata, encoding details, and a "
            "normalized EasyHarness result payload."
        ),
        common_failures=[
            "The target file does not exist.",
            "The target appears to be binary rather than text.",
            "The requested line range is invalid or escapes the configured scope.",
        ],
    )
    def fileglide_read_text(
        target: str,
        start_line: int | None = None,
        end_line: int | None = None,
        encoding: str | None = None,
    ) -> ToolOutput:
        """Read text file content."""

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_read_text",
            action=lambda: facade.text.read_text(
                root_text,
                target,
                encoding=encoding,
                start_line=start_line,
                end_line=end_line,
            ),
        )

    @tool(
        name="fileglide_search_text",
        purpose=(
            "Run regex-based text searches across text files inside the "
            "configured scope."
        ),
        when_to_use=(
            "Use this when the model needs grep-like text search for symbols, "
            "patterns, snippets, or call sites across the scoped workspace."
        ),
        parameters={
            "pattern": "Regular expression used to search text content.",
            "start": (
                "Search starting point. Relative and absolute paths are "
                "accepted, but the path must stay within the configured scope."
            ),
            "recursive": "Whether to recurse into child directories.",
            "max_depth": "Maximum recursion depth, or None for no explicit cap.",
            "include": "Optional include patterns.",
            "exclude": "Optional exclude patterns.",
            "encoding": "Optional explicit text encoding.",
        },
        returns=(
            "Structured match results with file paths, line numbers, matched "
            "text, and a normalized EasyHarness result payload."
        ),
        common_failures=[
            "The regular expression is invalid.",
            "The starting path does not exist or escapes the configured scope.",
        ],
    )
    def fileglide_search_text(
        pattern: str,
        start: str = ".",
        recursive: bool = True,
        max_depth: int | None = None,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        encoding: str | None = None,
    ) -> ToolOutput:
        """Search text content with a regular expression."""

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_search_text",
            action=lambda: facade.search.regex_search(
                root_text,
                pattern=pattern,
                start=start,
                recursive=recursive,
                max_depth=max_depth,
                include=_normalize_patterns(include),
                exclude=_normalize_patterns(exclude),
                encoding=encoding,
            ),
        )

    @tool(
        name="fileglide_edit_text",
        purpose=(
            "Perform overwrite, append, insert, line replacement, or "
            "anchor-based insertion within scoped text files."
        ),
        when_to_use=(
            "Use this when the model already knows the intended text change and "
            "needs precise scoped editing. For higher-risk edits, callers "
            "should read context before writing."
        ),
        parameters={
            "action": "Edit action: write, replace_lines, or insert_anchor.",
            "target": "Path to the text file that should be edited.",
            "content": "Text content to write or insert.",
            "start_line": "First line number for replace_lines.",
            "end_line": "Last line number for replace_lines.",
            "anchor": "Unique anchor string used by insert_anchor.",
            "before": "Whether insert_anchor should insert before the anchor.",
            "mode": "Write mode for write: overwrite, append, or insert.",
            "position": "Character position used by write when mode is insert.",
            "encoding": (
                "Optional explicit encoding. When omitted, fileglide will "
                "handle encoding automatically."
            ),
        },
        returns=(
            "Structured edit results with file metadata, encoding details, and "
            "a normalized EasyHarness result payload."
        ),
        common_failures=[
            "The action does not match the required parameters.",
            "The target is outside scope or is not editable text.",
            "The line range is invalid or the anchor is not uniquely located.",
        ],
    )
    def fileglide_edit_text(
        action: str,
        target: str,
        content: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        anchor: str | None = None,
        before: bool = False,
        mode: str = "overwrite",
        position: int | None = None,
        encoding: str | None = None,
    ) -> ToolOutput:
        """Perform precise text edits."""

        def run_action() -> dict[str, Any]:
            if action == "write":
                return facade.text.write_text(
                    root_text,
                    target,
                    content=_require_text_content(action, content),
                    content_source=content_source,
                    mode=mode,
                    encoding=encoding,
                    position=position,
                )
            if action == "replace_lines":
                if start_line is None or end_line is None:
                    raise ValidationError(
                        code="missing_line_range",
                        message="replace_lines requires start_line and end_line.",
                        details={"action": action},
                    )
                return facade.text.replace_lines(
                    root_text,
                    target,
                    start_line=start_line,
                    end_line=end_line,
                    content=_require_text_content(action, content),
                    content_source=content_source,
                    encoding=encoding,
                )
            if action == "insert_anchor":
                if not anchor:
                    raise ValidationError(
                        code="missing_anchor",
                        message="insert_anchor requires a non-empty anchor.",
                        details={"action": action},
                    )
                return facade.text.insert_by_anchor(
                    root_text,
                    target,
                    anchor=anchor,
                    content=_require_text_content(action, content),
                    content_source=content_source,
                    before=before,
                    encoding=encoding,
                )
            raise ValidationError(
                code="invalid_edit_action",
                message="Action must be write, replace_lines, or insert_anchor.",
                details={"action": action},
            )

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_edit_text",
            action=run_action,
        )

    @tool(
        name="fileglide_manage_paths",
        purpose=(
            "Manage files and directories, including creation, existence "
            "checks, delete preview or confirmation, and scoped moves."
        ),
        when_to_use=(
            "Use this when the model needs to create paths, confirm whether a "
            "path exists, preview delete impact, or perform confirmable move "
            "operations. Delete and move are higher-risk actions, so prefer "
            "dry_run before executing the final change."
        ),
        parameters={
            "action": "Management action: create, exists, delete, or move.",
            "kind": "Target type: file or directory.",
            "target": "Target path used by create, exists, and delete.",
            "source": "Source path used by move.",
            "destination": "Destination path used by move.",
            "parents": "Whether create should make missing parent directories.",
            "exist_ok": "Whether create should allow an existing target.",
            "recursive": (
                "Whether delete on a directory should recurse into non-empty "
                "directories."
            ),
            "dry_run": (
                "Whether delete or move should return a preview instead of "
                "making the change."
            ),
            "confirm": "Whether delete or move should perform the real change.",
            "missing_ok": "Whether delete should allow a missing target.",
        },
        returns=(
            "Structured path-management results with preview information and a "
            "normalized EasyHarness result payload."
        ),
        common_failures=[
            "The action or kind argument is invalid.",
            "Delete or move is rejected without confirm when dry_run is false.",
            "The target escapes scope, already exists, is missing, or has the "
            "wrong type.",
        ],
    )
    def fileglide_manage_paths(
        action: str,
        kind: str = "file",
        target: str | None = None,
        source: str | None = None,
        destination: str | None = None,
        parents: bool = True,
        exist_ok: bool = True,
        recursive: bool = False,
        dry_run: bool = False,
        confirm: bool = False,
        missing_ok: bool = False,
    ) -> ToolOutput:
        """Create, inspect, delete, or move paths."""

        def run_action() -> dict[str, Any]:
            _validate_manage_action(action, kind)

            if action == "create":
                if not target:
                    raise ValidationError(
                        code="missing_target",
                        message="create requires target.",
                        details={"action": action},
                    )
                if kind == "file":
                    return facade.filesystem.create_file(
                        root_text,
                        target,
                        parents=parents,
                        exist_ok=exist_ok,
                    )
                return facade.filesystem.create_path(
                    root_text,
                    target,
                    parents=parents,
                    exist_ok=exist_ok,
                )

            if action == "exists":
                if not target:
                    raise ValidationError(
                        code="missing_target",
                        message="exists requires target.",
                        details={"action": action},
                    )
                return facade.filesystem.exists(root_text, target)

            if action == "delete":
                if not target:
                    raise ValidationError(
                        code="missing_target",
                        message="delete requires target.",
                        details={"action": action},
                    )
                if kind == "file":
                    return facade.filesystem.delete_file(
                        root_text,
                        target,
                        dry_run=dry_run,
                        confirm=confirm,
                        missing_ok=missing_ok,
                    )
                return facade.filesystem.delete_path(
                    root_text,
                    target,
                    recursive=recursive,
                    dry_run=dry_run,
                    confirm=confirm,
                    missing_ok=missing_ok,
                )

            if not source or not destination:
                raise ValidationError(
                    code="missing_move_paths",
                    message="move requires source and destination.",
                    details={"action": action},
                )
            if kind == "file":
                return facade.filesystem.move_file(
                    root_text,
                    source,
                    destination,
                    dry_run=dry_run,
                    confirm=confirm,
                )
            return facade.filesystem.move_path(
                root_text,
                source,
                destination,
                dry_run=dry_run,
                confirm=confirm,
            )

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_manage_paths",
            action=run_action,
        )

    @tool(
        name="fileglide_inspect_path",
        purpose=(
            "Inspect path size or read raw bytes from a binary file segment "
            "inside the configured scope."
        ),
        when_to_use=(
            "Use this when the model needs path-size information or has to "
            "inspect a byte range from a binary file."
        ),
        parameters={
            "action": "Inspection action: size or read_bytes.",
            "target": "Path that should be inspected.",
            "offset": "Byte offset used by read_bytes.",
            "length": (
                "Number of bytes to read for read_bytes, or None to read "
                "through the end."
            ),
        },
        returns=(
            "Structured size data or byte-read results with a normalized "
            "EasyHarness result payload."
        ),
        common_failures=[
            "The action argument is invalid.",
            "The target does not exist or escapes the configured scope.",
            "The byte offset is invalid.",
        ],
    )
    def fileglide_inspect_path(
        action: str,
        target: str,
        offset: int = 0,
        length: int | None = None,
    ) -> ToolOutput:
        """Inspect path size or read raw bytes."""

        def run_action() -> dict[str, Any]:
            _validate_inspect_action(action)
            if action == "size":
                return facade.sizing.stat_size(root_text, target)
            return facade.binary.read_bytes(
                root_text,
                target,
                offset=offset,
                length=length,
            )

        return _run_fileglide(
            root=resolved_root,
            operation="fileglide_inspect_path",
            action=run_action,
        )

    return [
        fileglide_list_tree,
        fileglide_search_paths,
        fileglide_read_text,
        fileglide_search_text,
        fileglide_edit_text,
        fileglide_manage_paths,
        fileglide_inspect_path,
    ]
