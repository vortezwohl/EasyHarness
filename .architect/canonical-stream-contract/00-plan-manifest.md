# Plan Manifest

## Metadata
- Document Type: Plan Manifest
- Document ID: PLAN
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN
- Plan Digest: cb0bfc4dab3945205ef45bbdeb15d94aaf3f8d959b1271a549d57fee096bbd09

## Objective
- 以唯一、追加式的 `AgentEvent` 协议替换当前含糊的文本事件语义，使 thinking 和 assistant 的每段文本至多发送一次，且终态不重放累计文本。

## Non-Goals
- 不保留旧 `AgentEvent.text`、`status`、`name` 或运行期兼容分支。
- 不修改模型供应商适配、会话历史、工具业务逻辑、前端或持久化。
- 不引入事件存储、回放或订阅总线。

## Approved Design Bundle
- Design IDs: D-001, D-002
- Approval Evidence: 用户在完整设计包后的首个后续回合明确选择破坏性重构（`2`），并以 `.w` 显式调用 `architect-propose`；未拒绝任何设计单元。
- Bundle Summary: 用 `sequence`、`phase_id`、`kind`、`operation`、`delta`、`error` 和 `data` 组成唯一公开事件；私有 Adapter 将各来源规整为 signal，再按 phase 生命周期投影。

## Architect Build Entry Conditions
- D-001 和 D-002 已完整记录，所有任务只引用其规则。
- 状态和执行日志已由计划工具初始化。
- 必须按 T-001、T-002、T-003 顺序执行；遇到无法改造的消费者按冲突协议停止。
