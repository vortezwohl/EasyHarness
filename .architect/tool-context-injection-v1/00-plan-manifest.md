# Plan Manifest

## Metadata
- Document Type: Plan Manifest
- Document ID: PLAN
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN
- Plan Digest: 77cc9392ffd3f55abeca181e3331e6bf4c2e8a7d3ee5801ca3f3edf0c654cc35

## Objective
Add per-turn, annotation-driven hidden ToolContext injection for EasyHarness tools. Context crosses only private invocation state and never the model schema, messages, default tool event input, or ToolResult.

## Non-Goals
- No DI container, factory, global/thread-local Context, serialization, persistence, authorization, or generic ToolOutput redaction.
- No Agent-held or shared-Tool-held default Context.

## Approved Design Bundle
- D-001: ToolContext marker and hidden-parameter classification.
- D-002: Per-turn explicit injection via invocation state.
- D-003: Visibility and safe-failure boundary.
- Approval Evidence: The user supplied D-001 through D-003 and explicitly invoked architect-propose on 2026-07-22.

## Architect Build Entry Conditions
- Run only after the user manually invokes architect-build.
- Execute T-001 through T-004 in order and update the centralized state and execution log.
- Stop for any conflict with hidden, per-turn, name-matched, non-leaking Context behavior.
