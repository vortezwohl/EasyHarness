# Task: T-001-public-event-contract

## Metadata
- Document Type: Task
- Document ID: T-001
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-N001
- Prohibited New Concepts: 旧协议兼容、schema 版本、事件存储、前端去重。

## Preconditions
- 搜索当前 AgentEvent 字段的 SDK 内部引用和 README 示例，确认没有未记录的公开字段消费者。

## Functional Boundary
- Requested Functionality: 定义只用 delta 承载新增文本的新 AgentEvent，并使所有字段组合可校验。
- Protected Functionality: 事件顺序、工具结构化数据和 Agent.stream() 迭代接口。
- Explicit Non-Goals: 不实现 signal 适配器，不修改模型和会话行为。
- Compatibility Guarantees: 不兼容旧 text/status/name；新字段无歧义。
- Mandatory Stop Condition: 若类型设计必须保留旧字段或为旧消费者提供分支，停止升级。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/types.py` | `AgentEvent`、事件 Literal | 定义 sequence、phase_id、kind、operation、delta、error、data 及组合校验 | D-001 要求唯一文本通道。 |
| `easyharness/__init__.py` | 公开导出 | 仅导出新公共类型需要的名称 | 保持根导出最小。 |
| `tests/test_sdk.py` | 公共类型测试 | 调整断言以匹配新字段 | 防止旧字段残留。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 公开类型定义和直接导出是唯一实现边界。
- Scope Expansion Decision Rule: 仅当类型引用无法编译时纳入直接调用点；不得预先改造运行时。
- Required Assessment and Record: 记录新增路径、引用符号及其与 D-001 的关系。

## MUST DO
- M-T001-001: 对 operation、delta、error 的合法组合建立不可绕过的校验。
- M-T001-002: 删除旧字段，确保类型与文档不同时暴露两种语义。

## MUST NOT DO
- N-T001-001: 不引入 schema_version、isV2、别名属性或默认兼容值。

## Atomic Steps
1. 搜索公开事件字段的引用并记录最小调用面。
2. 以新信封替换 AgentEvent 和相关 Literal，加入字段组合校验与中文 docstring。
3. 更新直接导出及类型级测试，执行测试切片。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 不可改造消费者或受保护迭代/工具关联要求旧字段。
- Required Conflict Analysis: 列出消费者、旧/新事件实例、受保护行为风险和最小变更路径。
- Recommended Option: `1` 改造或删除消费者，保持单一协议。
- Recommendation Rationale: 用户已批准破坏性重构；双协议会重现废弃的复杂性。
- Decision Prompt: 请在 `1` 改造或删除旧消费者，或 `2` 允许一次性兼容层之间选择。
- Decision Limit: 获得用户选择前不得进入 T-002。
- Required Decision Record: 将选择、理由、影响和验证要求写入执行日志与状态文件。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 改造或删除旧消费者 | 保持完整单协议 | 不改变受保护运行时行为 | 旧字段彻底消失 | 类型测试和调用方迁移测试。 |
| 2 | 允许一次性兼容层 | 偏离批准设计 | 增加协议歧义风险 | 重新引入旧兼容 | 必须回到 architect-design。 |

## Required Verification Evidence
- Verification Procedure: 运行类型/单元测试切片并检查公开字段搜索结果。
- Required Evidence: 新事件实例合法性、非法字段组合拒绝、旧字段不存在。

## Completion Criteria
- 新公共契约独立可验证，旧文本语义不再存在，且 T-002 可以仅依赖该契约实现投影。
