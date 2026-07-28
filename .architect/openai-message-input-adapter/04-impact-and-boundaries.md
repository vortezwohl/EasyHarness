# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN

## Functional Boundary
仅实现并验证 D-001 的严格输入 Adapter：字符串和允许的 OpenAI Chat Completions 文本/function-tool 列表均转成 Strands `Messages` 后调用现有运行时。

## Protected Functionality
字符串兼容、列表追加历史、构造期系统提示、工具 Context 私有注入、事件映射、取消、压缩、会话复用和并发占用均必须保持。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/runtime.py` | `_StrandsRuntime.run`、`_StrandsRuntime.stream`、`Agent.run`、`Agent.stream` | 增加单一私有规范化函数并更新输入类型和文档。 | 当前四个入口直接接收字符串，是唯一需要在传递给 Strands 前转换的位置。 |
| `tests/test_sdk.py` | `FakeModel`、`EasyHarnessSdkTests` | 记录底层消息并覆盖正常、失败和兼容场景。 | 已有无需真实模型的运行时和工具历史测试设施。 |
| `README.md` | 运行入口示例与 API 说明 | 说明允许格式、追加语义和系统角色拒绝。 | 新增公开输入契约必须对调用方可见。 |

## Impact Scope Audit Findings
未发现需要修改模型格式化、工具执行或会话管理模块的证据。若运行时事实显示 Strands 对规范化列表存在未覆盖的入口约束，可在不改变 D-001 功能边界的前提下谨慎扩展测试或运行时邻近代码，并记录原因。

## Functional Boundary Conflict Readiness
若实现需要保留 `system` / `developer`、支持非文本 content、替换会话或执行历史工具调用，build 必须停止，说明 Strands 约束、受影响兼容面和最小替代方案，并请求用户裁决；不得自行扩大功能。
