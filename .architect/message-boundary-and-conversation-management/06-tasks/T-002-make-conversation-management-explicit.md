# Task: T-002-make-conversation-management-explicit

## Metadata
- Document Type: Task
- Document ID: T-002
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Design Sources
- Source Design References: D-002
- Design Rule References: R-D002-001, R-D002-002, R-D002-003, R-D002-004, R-D002-N001, R-D002-N002, R-D002-N003
- Prohibited New Concepts: manager factory、全局默认配置、额外导出、不可 deepcopy manager 的新 reset 协议。

## Preconditions
确认 Strands None 默认值为 SlidingWindowConversationManager，NullConversationManager 的溢出语义，以及 clone/reset/event sink 行为。

## Functional Boundary
- Requested Functionality: 默认显式使用 NullConversationManager；根包仅公开指定 Eventing 与 Sliding 类型。
- Protected Functionality: 显式 manager、deepcopy 回退、event sink、reset 并发保护、会话追加和工具事件。
- Explicit Non-Goals: 默认摘要、默认滑动窗口、额外 manager 导出、新抽象或不可 deepcopy manager 保证。
- Compatibility Guarantees: 仅默认管理行为改变；显式 manager 与事件保持。
- Mandatory Stop Condition: 需要改变 reset 生命周期、导出额外类型或让默认路径再次管理历史时停止。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/conversation.py | clone_conversation_manager | None 创建新的 NullConversationManager。 | 绕过 Strands None 默认窗口。 |
| easyharness/_internal/runtime.py | Agent manager docstring | 更新默认行为英文描述。 | 当前文案仍称默认摘要。 |
| easyharness/__init__.py | imports and __all__ | 只添加两个指定导出。 | 用户限制根包范围。 |
| tests/test_sdk.py | manager/reset tests | 更新默认断言并验证显式 manager。 | 保护新默认与 opt-in。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 默认构造、公开导出与相邻测试已覆盖已知所有者。
- Scope Expansion Decision Rule: 仅导入循环或公开文档验证要求时，最小扩展到 README。
- Required Assessment and Record: 记录新增路径、导入/生命周期证据、默认语义和定向测试。

## MUST DO
- M-T002-001: None 路径显式创建新的 NullConversationManager。
- M-T002-002: 仅导出两个用户指定类型，并保持既有根包符号。
- M-T002-003: 保留显式 manager 的 clone、event sink 和 reset 模板语义。

## MUST NOT DO
- N-T002-001: 默认路径不得摘要、裁剪或发射 compress event。
- N-T002-002: 不得把 None 直接传给 Strands。
- N-T002-003: 不得导出其他会话类型或顺手重构 manager 架构。

## Atomic Steps
1. 复核 Strands 构造默认值和 Null 溢出行为。
2. 修改 conversation 默认、公开导出和英文 API 文案。
3. 调整默认、显式 Eventing、显式 Sliding、reset 测试。
4. 运行会话管理定向测试。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 默认不压缩无法在当前 Strands 生命周期实现，或需要改变 reset/导出语义。
- Required Conflict Analysis: 列出构造路径、实际默认 manager、候选实现和对 reset/事件/API 的影响。
- Recommended Option: `1`。
- Recommendation Rationale: 显式 Null 默认直接满足用户边界且不引入新抽象。
- Decision Prompt: 请选择 `1` 维持显式 Null 默认，或 `2` 批准新的会话管理设计。
- Decision Limit: 仅解决默认 manager 语义；不得附带扩大导出或修改其他生命周期。
- Required Decision Record: 在执行日志和状态记录证据、决定、影响和验证。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 显式 Null 默认 | 默认完整保留历史。 | reset 和显式 manager 保持。 | 默认压缩被移除。 | 断言类型、事件和溢出路径。 |
| 2 | 用户批准新设计 | 当前任务停止。 | 重新界定生命周期。 | 可能新增迁移义务。 | 新设计后再实现。 |

## Required Verification Evidence
- Verification Procedure: 测试 manager 类型、压缩事件、显式 manager、reset 和根包导入。
- Required Evidence: 默认没有压缩；两个指定类型可导入；显式策略仍工作；reset 后旧会话不可见。

## Completion Criteria
默认路径不再管理或压缩历史，根包导出精确受限，显式 manager 与 reset 受保护行为通过定向验证。
