# Execution Log

## Metadata
- Document Type: Execution Log
- Document ID: EXECUTION-LOG
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

This document is append-only. The `architect-build` stage records only observed
execution, task-declared execution results, state transitions, impact-scope
adaptations, user-approved functional-boundary decisions, and other factual run
events after they occur.

- 2026-07-28T15:43:41+08:00: T-001 started. Rebuilt execution context from the sealed D-001 and task documents; no functional-boundary exception or impact-scope adaptation is active. The approved source scope is `easyharness/_internal/runtime.py`.
- 2026-07-28T15:47:00+08:00: T-001 completed. Added a shared strict Adapter in `easyharness/_internal/runtime.py` for `str | list[dict]`, mapping approved text/function-tool history into Strands `Messages` before both run and stream call Strands. `python -m compileall easyharness`, runtime import, and `git diff --check` passed. No impact-scope adaptation or functional-boundary exception occurred.
- 2026-07-28T15:48:00+08:00: T-002 started. The approved scope is `tests/test_sdk.py` and `README.md`; verification will use the existing FakeModel and no real model API.
- 2026-07-28T15:52:00+08:00: T-002 completed. Added FakeModel request snapshots plus regression coverage for string normalization, appended OpenAI text/function-tool history, system/developer rejection, malformed function arguments, input immutability, and post-failure Agent reuse. Updated README with the supported input subset and system-prompt boundary. The two new tests passed. `python -m compileall easyharness tests`, `git diff --check`, `validate_plan.py`, and UTF-8-without-BOM checks passed. `python -m unittest tests.test_sdk` ran 47 tests with one unrelated existing failure in `test_tool_context_deep_payload_validation_and_safe_failures`: the test expects a nested type string but the untouched ToolContext implementation reports payload type `dict`. Ruff could not run because it is not installed in `.venv`. No impact-scope adaptation or functional-boundary exception occurred.
- 2026-07-28T15:55:00+08:00: Completion audit reopened T-002 after finding that the new tests did not directly exercise a successful `Agent.run(list[dict])` call. This is a verification-evidence gap within the sealed task, not a functional-boundary change; the next action is to add the missing focused assertion and rerun the task checks.
- 2026-07-28T15:57:00+08:00: T-002 completed after audit repair. Added a direct successful `Agent.run(list[dict])` assertion that verifies the normalized Strands user message and preserved system prompt. The two input-adapter tests passed. The complete SDK suite again ran 47 tests and reproduced only the same unchanged ToolContext deep-payload assertion failure. This confirms the plan's input-adapter paths without expanding scope; Ruff remains unavailable because `.venv` has no ruff installation.
