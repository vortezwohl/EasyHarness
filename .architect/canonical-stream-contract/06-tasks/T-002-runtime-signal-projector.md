# Task: T-002-runtime-signal-projector

## Metadata
- Document Type: Task
- Document ID: T-002
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001, D-002
- Design Rule References: R-D001-001, R-D001-N001, R-D002-001, R-D002-N001
- Prohibited New Concepts: provider 适配公开泄漏、State 类层级、文本全文缓存、前端去重。

## Preconditions
- T-001 完成并记录新 AgentEvent 契约；取消、工具关联与压缩测试基线可运行。

## Functional Boundary
- Requested Functionality: 所有 Strands、工具与压缩来源经私有 signal 和单一投影器生成新事件，文本不重复。
- Protected Functionality: 单 Agent 互斥、工具 use ID 关联、取消/失败终结、压缩事件和 run 行为。
- Explicit Non-Goals: 不改变 provider 请求、会话管理策略或引入持久化流。
- Compatibility Guarantees: 新协议内 sequence 连续、phase_id 稳定；不保证旧字段。
- Mandatory Stop Condition: 若实现需要改变工具执行顺序、取消范围或模型消息历史以解决文本问题，停止升级。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/runtime.py` | `_EventMapper`、`_PhaseState`、worker | 替换为 signal 适配和 phase 投影调用 | 当前是歧义和多来源耦合中心。 |
| `easyharness/_internal/conversation.py` | `InternalEventSink` | 替换压缩魔法字典或适配为 signal | D-002 禁止跨层字典协议。 |
| `easyharness/_internal/tools.py` | tool stream marker | 保留 tool-use ID，改由 signal 驱动 | 工具是活动 phase 来源。 |
| 必要的私有流模块 | signal、phase registry、projector | 仅承载单一职责私有类型 | 允许隔离 Adapter 与投影。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 覆盖所有当前公共事件生产来源。
- Scope Expansion Decision Rule: 只有直接生产者无法通过现有私有边界转换时扩展；先说明来源、职责和最小替代方案。
- Required Assessment and Record: 记录 source-to-signal 映射、影响路径及是否触碰受保护行为。

## MUST DO
- M-T002-001: 单一投影器分配递增 sequence 和 phase_id；单一 finish_phase() 发出所有终态。
- M-T002-002: 有 assistant delta 时忽略 result 重复全文；无 delta 时只合成一次 fallback delta；thinking 永不从 result 生成快照。

## MUST NOT DO
- N-T002-001: 不保留 chunks 全文缓存、completed 文本、Strands 原始 key 公开泄漏或魔法 marker 双协议。

## Atomic Steps
1. 定义私有 signal 形状和来源适配边界，保留工具并发关联 identity。
2. 实现 phase registry/projector，处理 started、delta、terminal、notice、失败和取消。
3. 替换 runtime、工具与压缩来源的直接公共事件构造，删除全文 flush 逻辑。
4. 运行 mapper、取消、工具和压缩测试切片，定位受保护行为回归。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 上游流顺序要求改变工具/取消/会话受保护行为，或无法在单次 delta 通道表示必要信息。
- Required Conflict Analysis: 给出原始事件、signal、公开事件序列、受保护行为差异和替代实现。
- Recommended Option: `1` 增强私有 signal 映射。
- Recommendation Rationale: 文本唯一性不要求改变 Agent 生命周期；冲突通常是适配边界缺失。
- Decision Prompt: 请在 `1` 增强私有 signal 映射，或 `2` 改变受保护运行时行为之间选择。
- Decision Limit: 未裁决前不得以更改受保护行为方式继续。
- Required Decision Record: 将原始序列、选择、影响和新增验证记录进日志和状态文件。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 增强私有 signal 映射 | 保持单协议和唯一文本 | 保持工具/取消/会话 | 无旧协议恢复 | 来源到事件的序列测试。 |
| 2 | 改变受保护运行时行为 | 可能实现目标 | 破坏批准边界 | 需要重新设计 | 完整回归及新的用户批准。 |

## Required Verification Evidence
- Verification Procedure: 用 FakeModel 和直接 mapper 输入验证 reasoning、assistant、工具、取消、失败、压缩、并发工具。
- Required Evidence: 每条事件的 sequence、phase_id、operation、delta/error/data，以及 no-duplicate 断言。

## Completion Criteria
- 所有公开事件仅由投影器产生，thinking/assistant 终态无文本，且受保护行为测试通过。
