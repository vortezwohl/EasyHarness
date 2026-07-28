# Impact and Boundaries

## Metadata
- Document Type: Impact and Boundaries
- Document ID: IMPACT
- Plan Name: message-boundary-and-conversation-management
- Created At: 2026-07-28:18:03:09.416
- Document Language: zh-CN

## Functional Boundary
- 实现宽松但不静默丢失语义的消息 Adapter。
- 无 manager 时完整保留历史；显式 manager 时保留其策略。
- 更新最小公开文档和测试，说明默认不压缩与显式装配。

## Protected Functionality
- system/developer 拒绝，构造期 system_prompt 独占。
- 会话追加、reset、流式事件、取消、工具 Context 和显式 manager 不得回退。
- 工具历史只做数据转换，不自动执行。

## Code Impact Scope
| Likely Code Location | Relevant Symbol or Area | Expected Work | Evidence or Rationale |
| --- | --- | --- | --- |
| easyharness/_internal/runtime.py | PromptInput, _normalize_prompt, run, stream | 放宽可映射字段并保留核心失败。 | 唯一公开消息边界。 |
| easyharness/_internal/conversation.py | clone_conversation_manager | None 改为显式 NullConversationManager。 | 当前默认摘要装配点。 |
| easyharness/__init__.py | __all__ | 仅导出两个指定 manager。 | 根包当前无会话类型。 |
| tests/test_sdk.py | history and reset tests | 覆盖默认不压缩、显式 manager、宽松字段。 | 本地回归入口。 |
| README.md | Public usage | 说明显式 manager 与默认不压缩。 | 新公开 API 需可发现。 |

## Impact Scope Audit Findings
- pyproject.toml 的 Ruff 运行时依赖和全仓既有格式问题不属于批准功能。
- model.py 仅在 reasoning_content 能由现有 DeepSeek 路径消费时进入最小范围。
- 不可 deepcopy manager 的 reset 限制只记录和测试，不承诺新保证。

## Functional Boundary Conflict Readiness
无法无损表达的输入必须展示样例、Strands 约束、影响与严格拒绝/新增设计两条路径。推荐严格拒绝；扩展须用户批准。