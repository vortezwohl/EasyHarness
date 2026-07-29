# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Functional Boundary
- 用单一、破坏性的追加式事件契约替换旧文本语义；文本只在 delta 事件中发送一次，终态仅表达 phase 生命周期。

## Protected Functionality
- `Agent.run()` 最终文本与取消可复用性；`Agent.stream()` 同步有序消费；工具 use ID 关联；取消、失败、压缩和会话管理。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| `easyharness/_internal/types.py` | `AgentEvent`、事件 Literal | 替换公开字段和组合校验 | 旧 `text/status` 是协议歧义根源。 |
| `easyharness/_internal/runtime.py` | `_EventMapper`、`_PhaseState`、worker | 改为 signal 适配与 phase 投影 | 当前混合多个来源并累计全文。 |
| `easyharness/_internal/conversation.py` | `InternalEventSink` | 替换压缩魔法字典或适配为 signal | 当前跨模块传递非类型化 marker。 |
| `easyharness/_internal/tools.py` | 工具流 marker | 保留 tool-use ID 并改为 signal | 工具是活动 phase 来源。 |
| `tests/test_sdk.py` | FakeModel、mapper、stream 测试 | 精确事件序列和负向断言 | 当前未覆盖 reasoning 语义。 |
| `README.md`、`easyharness/__init__.py` | 文档与导出 | 更新唯一示例和公开表面 | 调用方必须迁移。 |

## Impact Scope Audit Findings
- 已覆盖公开类型、全部事件来源、同步 worker、测试和文档。
- `pyproject.toml` 仅在发布流程要求时更新破坏性版本；不扩大依赖范围。
- 未发现数据库、持久化数据或前端目录属于本计划影响面。

## Functional Boundary Conflict Readiness
- 若不可修改消费者依赖旧字段，构建必须记录调用方、行为差异和测试证据，停止并请求用户选择删除/改造消费者、允许一次性兼容或缩小发布范围；默认推荐删除/改造以保持单协议。
