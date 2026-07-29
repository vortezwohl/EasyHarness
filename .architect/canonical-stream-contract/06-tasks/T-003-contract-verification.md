# Task: T-003-contract-verification

## Metadata
- Document Type: Task
- Document ID: T-003
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001, D-002
- Design Rule References: R-D001-002, R-D001-N002, R-D002-001, R-D002-N002
- Prohibited New Concepts: 只靠 UI 观察、只覆盖 happy path、用文档替代事件断言。

## Preconditions
- T-001、T-002 均完成并记录局部测试；新公开契约和投影器可运行。

## Functional Boundary
- Requested Functionality: 用严格序列测试证明文本只出现一次，补齐 README 的唯一消费方式并完成项目验证。
- Protected Functionality: 既有工具、取消、压缩、会话和模型配置测试覆盖。
- Explicit Non-Goals: 不新增前端测试、网络依赖、持久化或旧协议示例。
- Compatibility Guarantees: 只文档化新协议，不保留旧字段迁移说明。
- Mandatory Stop Condition: 若测试显示修复必须恢复全文终态或改变受保护行为，停止并升级。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `tests/test_sdk.py` | FakeModel、事件 mapper、Agent.stream 测试 | 增加精确序列和负向断言 | 当前 50 项测试未覆盖 reasoning 语义。 |
| `README.md` | stream 示例和事件说明 | 更新为 operation/delta 消费方式 | 调用方需有唯一迁移目标。 |
| `pyproject.toml` | 发布版本 | 仅在发布流程要求时更新破坏性版本 | 新协议是公开破坏性变更。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 测试和公开文档是证明/交付该协议的最小面。
- Scope Expansion Decision Rule: 只有另一个 SDK 文档或公开示例仍描述旧字段时扩展。
- Required Assessment and Record: 记录旧引用、删改原因、最终搜索结果和验证命令。

## MUST DO
- M-T003-001: 断言完整事件序列而非只检查事件存在；覆盖 fallback、取消、失败和并发工具。
- M-T003-002: 验证每个文本字符一次、sequence 无缺口、phase_id 一致、终态无 delta。

## MUST NOT DO
- N-T003-001: 不以 UI 去重或宽松 contains 断言掩盖协议错误。
- N-T003-002: 不保留旧字段、旧协议或版本适配文档。

## Atomic Steps
1. 为 reasoning 后工具、assistant 多 delta、result fallback、取消、异常、压缩和同名并发工具建立精确断言。
2. 更新 README 事件字段说明和唯一消费循环，删除旧文本语义示例。
3. 运行 Ruff、完整 SDK 单测、旧字段搜索与 UTF-8/BOM 检查，记录结果。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 全量验证暴露受保护行为回归，且无法以已批准投影规则修复。
- Required Conflict Analysis: 给出失败测试、旧/新序列、最小代码路径、受保护行为影响和可选修复。
- Recommended Option: `1` 修正适配/投影实现。
- Recommendation Rationale: D-001/D-002 已固定协议和生命周期边界，失败首先代表实现偏差。
- Decision Prompt: 请在 `1` 修正适配/投影实现，或 `2` 重新设计边界之间选择。
- Decision Limit: 在用户裁决前不得发布或标记计划完成。
- Required Decision Record: 把失败、裁决、回归范围和验证结论写入执行日志与状态文件。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 修正适配/投影实现 | 保持完整目标 | 保持受保护行为 | 单协议不变 | 定向加全量测试。 |
| 2 | 重新设计边界 | 暂停当前目标 | 可能改变受保护行为 | 需要新批准 | 回到 architect-design。 |

## Required Verification Evidence
- Verification Procedure: `ruff check easyharness tests`、`D:\github-project\EasyHarness\.venv\Scripts\python.exe -m unittest tests.test_sdk -v`、旧字段搜索、UTF-8 without BOM 检查。
- Required Evidence: 命令输出、事件序列表、旧字段零命中或有意保留的非协议引用说明、README 新示例。

## Completion Criteria
- 所有指定序列及全量 SDK 测试通过，文档仅描述新协议，且验证记录足以证明没有 thinking/assistant 文本重放。
