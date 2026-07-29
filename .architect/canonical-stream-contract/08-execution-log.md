# Execution Log

## Metadata
- Document Type: Execution Log
- Document ID: EXECUTION-LOG
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Initialization
- Plan package created by `architect-propose`.
- Approved designs recorded: D-001, D-002.
- Task execution has not started. All tasks are pending.
- No implementation, test, configuration, dependency or database files were modified during planning.

## Execution Entries
- None. `architect-build` must append one factual entry per task transition, impact-scope adaptation, functional-boundary decision and verification result.

## T-001 开始
- 状态: in_progress。
- 实际行动: 已加载封存计划、D-001、全部未执行任务和当前状态。
- 边界: 仅定义新公开事件契约、根导出和直接类型测试；保护 Agent.stream() 有序迭代与工具结构化数据。
- 非目标: 不触及运行时映射、模型供应商、会话或工具执行行为。
- 停止条件: 如果存在不可改造的旧字段消费者，立即停止并升级，不恢复兼容层。

## T-001 影响范围调整
- 触发证据: 实际导入 easyharness 失败，runtime.py 仍导入已删除的 EventStatus。
- 新增路径: easyharness/_internal/runtime.py。
- 最小决定: 仅将直接类型导入与注解重命名为 EventOperation，不改事件映射、工具、取消、模型或会话行为。
- 边界判定: 未触及受保护功能，所以不触发用户裁决。

## T-001 完成
- 主要改动: AgentEvent 已替换为 sequence、phase_id、kind、operation、delta、error、started_at、duration_ms、data，并在构造期禁止终态文本回放、非 failed 错误和旧字段。
- 验证: easyharness 导入通过；test_agent_event_enforces_single_text_channel 通过；types.py、runtime.py、test_sdk.py 的 py_compile 通过。
- 字段审计: AgentEvent 不含 status、text 或 name；types.py 中的 model_text 与参数 name 是无关业务字段。
- 影响范围调整: runtime.py 的 EventStatus 直接引用已最小迁移为 EventOperation，以恢复包导入；尚未改造运行时事件投影。

## T-002 Start
- State: in_progress.
- Boundary: route Strands, tool, and compression sources through RuntimeSignal and one projector; preserve tool identity, cancellation, model requests, and conversation history.

## T-002 Adapter Decision
- Evidence: Strands 1.45 `ToolStreamEvent` stores a yielded value at `tool_stream_event.data`.
- Minimal decision: unwrap only a RuntimeSignal at that private location; unrecognized values are ignored.
- Boundary decision: no protected runtime behavior changed, so no user escalation was required.

## T-002 Complete
- Main changes: introduced typed RuntimeSignal sources for tools and compression; removed tool/compression magic marker dictionaries; centralized public AgentEvent creation, phase IDs, and sequence allocation in `_EventMapper`.
- Text behavior: phases do not store text; terminal events carry no delta; a result becomes one fallback assistant delta only when no assistant delta was observed.
- Verification: direct thinking/tool/assistant/result sequence passed; fallback, cancellation, and failure sequence assertions passed; compression signal slice passed; `py_compile` passed for runtime, conversation, tools, and streaming.
- Scope adaptation: the private Strands wrapper was handled in runtime only; no tool order, cancellation scope, model request, session history, or tool-use association changed.

## T-003 Start
- State: in_progress.
- Boundary: replace old public-event assertions with strict canonical sequence assertions and document the sole delta consumer loop.
- Stop condition: if verification requires restoring terminal text or changing protected runtime behavior, stop and escalate.

## T-003 Verification Adjustment
- Evidence: cancellation of active tool phases emitted terminal events without source data, so the terminal tool-use ID association was lost.
- Minimal correction: retain phase source data in _PhaseState and use it only when the terminal signal does not provide data.
- Boundary decision: this restores the protected tool-use association without changing tool order, cancellation scope, model requests, session history, or the single event contract.

## T-003 Complete
- Main changes: SDK fixtures now use RuntimeSignal, assert exact operations, phase correlation, continuous event order, one-time deltas, terminal delta absence, fallback, cancellation, failure, compression, and concurrent tool behavior.
- Documentation: README now presents one delta-only consumer loop and documents terminal lifecycle semantics and tool output in event.data.
- Verification: ruff check easyharness tests passed; python -m unittest tests.test_sdk -v passed (51 tests); python -m unittest tests.test_context_window_resolution -v passed (3 tests).
- Protocol audit: README has zero obsolete public protocol references. Remaining _easyharness_tool_contexts and _easyharness_tool_outputs references are private invocation-state keys, not public event fields or compatibility markers.
- Encoding: all modified source, test, and README files were checked as UTF-8 without BOM.