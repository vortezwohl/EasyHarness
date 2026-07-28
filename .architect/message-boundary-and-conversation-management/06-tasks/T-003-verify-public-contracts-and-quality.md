# Task: T-003-verify-public-contracts-and-quality

## Metadata
- Document Type: Task
- Document ID: T-003
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Design Sources
- Source Design References: D-001, D-002
- Design Rule References: R-D001-001, R-D001-002, R-D001-003, R-D001-004, R-D001-N001, R-D001-N002, R-D001-N003, R-D002-001, R-D002-002, R-D002-003, R-D002-004, R-D002-N001, R-D002-N002, R-D002-N003
- Prohibited New Concepts: 全仓格式化、无关翻译、额外功能、默认压缩恢复、额外导出。

## Preconditions
T-001 与 T-002 已完成定向验证；记录当前完整 SDK 的既有 ToolContext 失败和全仓 Ruff 基线。

## Functional Boundary
- Requested Functionality: 验证消息、默认会话、显式 manager、reset、根包导出与英文质量要求；提供最小使用文档。
- Protected Functionality: 仅修改计划相关测试和文档，不掩盖或修复无关基线失败。
- Explicit Non-Goals: 全仓 lint 修复、全仓格式化、中文历史文案翻译、额外公开 API。
- Compatibility Guarantees: D-001/D-002 受保护功能保持，失败报告真实且可区分。
- Mandatory Stop Condition: 达成质量门禁必须修改无关模块，或文档需要承诺未实现能力时停止。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| tests/test_sdk.py | public behavior tests | 组合消息、会话、reset、导出与失败回归。 | 主要离线证据。 |
| README.md | explicit manager usage | 说明默认不压缩和 opt-in manager。 | 新 API 应可发现。 |
| changed Python files | lint and encoding | Ruff、format、UTF-8/BOM。 | 用户要求 PEP 8 与英文文案。 |

## Impact Scope Expansion Procedure
- Initial Scope Rationale: 测试、README 与已改 Python 文件足以验证公开契约。
- Scope Expansion Decision Rule: 仅当定向验证指出遗漏的同一公开契约文件时扩展，不得因全仓噪音扩张。
- Required Assessment and Record: 记录新路径、失败归属、因果证据和最小验证。

## MUST DO
- M-T003-001: 覆盖宽松输入、核心拒绝、默认不压缩、显式两个 manager、reset 和根包导出。
- M-T003-002: 对本计划修改的 Python 文件执行 Ruff lint、format check、UTF-8 无 BOM 检查。
- M-T003-003: 在 README 用最小示例说明默认不压缩和显式 manager；示例文案使用英文。
- M-T003-004: 区分定向通过与完整 SDK 的既有失败。

## MUST NOT DO
- N-T003-001: 不得将既有 ToolContext 或无关 Ruff 失败归因为本计划。
- N-T003-002: 不得全仓格式化或翻译未触及文件。
- N-T003-003: 不得声称多模态、完整历史校验或不可 deepcopy manager reset 已支持。

## Atomic Steps
1. 汇总并运行 D-001、D-002 行为回归。
2. 更新 README 最小使用示例并复核公开导入。
3. 对触及 Python 文件运行 Ruff 和编码检查。
4. 运行完整 SDK 测试，分别报告计划回归和既有失败。
5. 记录无法自动验证的剩余风险。

## Functional Boundary Conflict Protocol
- Escalation Trigger: 定向质量或文档要求修改计划外模块，或既有基线失败掩盖计划结果。
- Required Conflict Analysis: 明确失败命令、关联文件、因果证据、最小范围和替代验证。
- Recommended Option: `1`。
- Recommendation Rationale: 定向验证与诚实基线报告可确认本计划，同时避免无关扩张。
- Decision Prompt: 请选择 `1` 保持定向门禁并报告基线，或 `2` 批准扩大范围修复具体基线。
- Decision Limit: 只决定列出的具体基线问题，不批准全仓整理。
- Required Decision Record: 在执行日志和状态记录命令、输出摘要、因果判断、决定和后续验证。

### Resolution Options
| Number | Resolution Path | Effect on Requested Functionality | Effect on Protected Functionality | Compatibility Consequences | Required Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 定向门禁与基线报告 | 完成本计划质量验证。 | 不触及无关代码。 | 基线问题单独存在。 | 定向 Ruff、编码、回归和完整测试报告。 |
| 2 | 用户批准具体扩展 | 当前任务暂停相关工作。 | 影响范围重新评估。 | 可能引入额外修改。 | 对新增范围定义独立验证。 |

## Required Verification Evidence
- Verification Procedure: 执行定向测试、Ruff、format、编码、公开导入检查和完整 SDK 测试。
- Required Evidence: 定向通过；全量失败按既有/新引入归属；README 与实际导出一致。

## Completion Criteria
批准公开契约已由测试和文档覆盖，修改文件满足英文、PEP 8、编码门禁，剩余基线风险已如实记录。
