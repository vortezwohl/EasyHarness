# Task: T-002-verify-and-document-message-input

## Metadata
- Document Type: Task
- Document ID: T-002
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001
- Design Rule References: R-D001-001, R-D001-002, R-D001-003, R-D001-004, R-D001-N001, R-D001-N002, R-D001-N003
- Prohibited New Concepts: 未批准输入格式、协议宽容解析、会话替换或工具重放。

## Preconditions
T-001 已完成；测试替身能够记录进入模型的 `Messages` 与系统提示；README 当前运行入口说明已定位。

## Functional Boundary
- Requested Functionality: 为适配器建立正常、边界和失败回归，并以最小 README 说明新公开输入。
- Protected Functionality: 字符串兼容、系统提示独立性、列表追加、现有 Context/取消/会话测试。
- Explicit Non-Goals: 真实 OpenAI 网络调用、provider 兼容矩阵、多模态和新的配置选项。
- Compatibility Guarantees: 现有 SDK 回归套件仍通过；文档不承诺未支持的 OpenAI 格式。
- Mandatory Stop Condition: 测试表明必须改变 D-001 的严格拒绝或追加语义才能通过时停止。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `tests/test_sdk.py` | `FakeModel`、`EasyHarnessSdkTests` | 记录底层输入并新增 input-adapter 回归。 | 当前测试无需真实 API，且已覆盖会话与工具历史。 |
| `README.md` | 快速开始、运行入口或公共能力说明 | 添加简洁 OpenAI 历史输入示例和拒绝规则。 | 输入类型是公开 SDK 行为。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 测试和 README 是实现行为的最小验证与交付面。
- Scope Expansion Decision Rule: 只有发现现有测试隔离不足或 README 已有同一 API 参考位置时才扩展到直接相邻位置。
- Required Assessment and Record: 记录新增测试/文档位置、证明的契约以及是否覆盖受保护功能。

## MUST DO
- M-T002-001: 覆盖 str、文本多轮列表、assistant tool_calls、tool result、历史追加、输入不变、系统提示独立性。
- M-T002-002: 覆盖 `system`、`developer`、未知 role、未知字段、坏 JSON arguments 与非 object arguments 的失败路径。
- M-T002-003: 对 run 与 stream 验证等价的输入契约；执行聚焦 SDK 测试、静态检查和 diff 检查。

## MUST NOT DO
- N-T002-001: 不得通过真实 API 或密钥验证，不得修改无关测试和文档。
- N-T002-002: 不得把未支持的格式写成已支持，或将未执行的验证表述为通过。

## Atomic Steps
1. 扩展 FakeModel 或测试辅助设施，以观察模型收到的规范化消息和系统提示。
2. 添加批准映射、追加历史、输入不变和 run/stream 对称回归。
3. 添加所有严格拒绝路径以及失败后 Agent 可继续使用的回归。
4. 更新 README，说明 `str | list[dict]`、支持子集、追加语义与系统角色拒绝。
5. 执行聚焦 SDK 测试、Ruff、编译检查与 `git diff --check`，记录事实结果。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 可复现测试显示批准映射破坏字符串兼容、系统提示所有权或列表追加语义。
- Required Conflict Analysis: 给出最小失败输入、实际 Strands 历史/模型参数、受影响契约、根因和候选最小修正。
- Recommended Option: `1` 保持 D-001 的严格边界，修正实现或测试替身以反映真实契约。
- Recommendation Rationale: 已批准设计优先保护会话与系统提示语义，不能用放宽输入掩盖回归。
- Decision Prompt: 请确认 `1` 修正当前实现以恢复批准契约，或 `2` 批准改变该契约。
- Decision Limit: 仅限复现到的契约冲突，不能扩展为多模态、会话替换或 provider 兼容项目。
- Required Decision Record: 在执行日志和状态文件记录失败、根因、选项、决定、修改与最终验证。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 修正实现或测试以恢复 D-001 | 保持批准输入适配。 | 保持所有受保护语义。 | 无新增迁移要求。 | 重新运行受影响测试和完整聚焦套件。 |
| 2 | 用户批准契约变更 | 当前任务停止，转入新设计。 | 需重新评估系统提示、历史或格式影响。 | 可能需要文档和迁移说明。 | 新设计定义新的回归矩阵。 |

## Required Verification Evidence
- Verification Procedure: 运行 `python -m unittest tests.test_sdk`、`python -m compileall easyharness`、`python -m ruff check easyharness tests` 和 `git diff --check`；无可用 Ruff 时如实记录。
- Required Evidence: 测试输出、静态检查输出和 diff 检查均记录在执行日志；README 示例与实际接受的子集一致。

## Completion Criteria
所有 D-001 verification seams 均有自动化断言，公开文档准确描述边界，且验证结果可审计；未越过任何非目标。
