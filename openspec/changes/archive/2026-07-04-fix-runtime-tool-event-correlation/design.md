## Context

当前 `easyharness/_internal/runtime.py` 中的 `_EventMapper` 只维护一个 `_tool` 槽位来表示“当前活动工具阶段”。这个建模默认假设任意时刻只会有一个工具阶段处于 started 与 terminal 之间，但 EasyHarness 的底层工具事件并没有给出这样的保证。只要出现“第二个 started 先于第一个 completed/failed 到达”的重叠场景，后一个 started 就会覆盖前一个状态，之后 `_complete_tool_phase()` 又会优先读取这个被覆盖的 tracked 状态，从而把第一个工具的终态错误地绑定到第二个工具调用上。

这类错误直接破坏的是 SDK 的公开事件契约，而不是某个上层 UI 的局部 reducer。上层消费者依赖 `tool_use_id`、`name`、`input`、`started_at` 与 `duration_ms` 关联 started 和 terminal 事件；一旦这些字段串线，时间线归约、运行态收口、调试展示与取消逻辑都会出现错误判断。

当前修复有几个硬约束：

- 不新增新的顶层公开 API，也不引入新的 runtime 并发模型；
- 不修改工具执行器已经稳定输出的 `tool_use_id` 协议；
- 不把修复做成 TUI 特判，而是修正公共 `_EventMapper`；
- 必须补上可复现此缺陷的最小回归测试，防止后续再次退化为“最近一次 started 覆盖前一次”。

## Goals / Non-Goals

**Goals:**

- 让公开工具终态事件始终与其原始工具调用精确关联，即使多个工具阶段发生重叠。
- 保证 `tool_use_id`、`name`、`input`、`started_at` 和持续时间来源不会从其他活动工具调用窃取。
- 让取消路径在存在多个活动工具阶段时也能输出完整、可归约的公共终态事件序列。
- 用最小实现边界修复 `_EventMapper`，不扩散到不相关模块。

**Non-Goals:**

- 不把 EasyHarness 升级为支持多个公开 `Agent` invocation 并发运行的 runtime。
- 不重写工具执行器，也不改变其 `easyharness_tool` 事件格式。
- 不新增新的 `AgentEvent.kind`、新的顶层导出或新的依赖。
- 不借这次修复顺手重构 thinking / assistant 阶段状态机。

## Decisions

### 1. 用按 `tool_use_id` 关联的活动工具表替代单个 `_tool` 槽位

**Decision**

将 `_EventMapper` 中的单个 `_tool: _ToolPhaseState | None` 替换为按 `tool_use_id` 索引的活动工具状态表。每次 `tool.started` 到达时写入对应调用的状态；每次 `tool.completed`、`tool.failed` 或 `tool.cancelled` 到达时按相同 `tool_use_id` 定位并移除对应状态。

**Rationale**

底层工具事件本来就已经提供稳定的 `tool_use_id`，这是最直接、最小且最不脆弱的关联键。按调用 ID 建模可以自然覆盖：

- 同名工具重叠；
- 异名工具重叠；
- 一个 started 之后另一个 started 先到，再由第一个先结束的乱序终态。

这比按“最近一个 started”或按“工具名”关联都更稳，因为后两者都无法区分同名并发调用。

**Alternatives considered**

- 保留单个 `_tool` 槽位并在终态时更多依赖原始事件字段：只能缓解部分字段串线，无法为取消与持续时间计算提供稳定的原始 started 上下文。
- 按工具名维护状态：同名工具重叠时仍会冲突，无法解决当前已复现缺陷。
- 引入更重的阶段对象或公开会话控制器：超出本次最小修复边界。

### 2. 终态事件只允许读取“匹配调用”的 tracked 状态，未匹配时退回原始终态载荷

**Decision**

`_complete_tool_phase()` 只在成功按 `tool_use_id` 找到匹配活动状态时，才使用 tracked 的 `started_at`、计时起点、`name` 与 `input`。若当前终态事件缺少 `tool_use_id` 或找不到匹配状态，则直接使用终态事件自身携带的字段生成公共事件，并且不得消费其他活动工具状态作为兜底。

**Rationale**

当前 bug 的根因就是“错误地拿了别人的 tracked 状态”。因此安全兜底原则应该是“宁可信息变少，也不能串线”。在未匹配场景下退回原始终态载荷，至少不会把别的调用错误归并过来。

**Alternatives considered**

- 终态未匹配时继续取最近一个活动工具：这正是当前缺陷模型，必须禁止。
- 终态未匹配时直接丢弃事件：会让公共流出现 started 无终态的更严重契约缺口。

### 3. 取消路径要关闭所有活动工具阶段，而不是只关闭一个“当前工具”

**Decision**

当底层结果表示 invocation 被取消，且 mapper 内仍有一个或多个活动工具阶段时，取消路径必须为每个活动工具调用发出对应的 `tool.cancelled` 终态，再发出最终的 `system.cancelled` 收口事件。取消事件的发出顺序应保持稳定，优先按 started 进入顺序输出。

**Rationale**

一旦修复了活动工具的真实建模，取消路径也必须与之保持一致。否则即便完成/失败能正确关联，取消仍会遗漏部分 started 阶段，导致上层时间线永远悬挂。

**Alternatives considered**

- 保持当前“只取消一个工具阶段”的逻辑：与新的状态模型不一致，且在重叠工具场景下仍会留下悬挂事件。
- 只发 `system.cancelled` 不补发工具终态：上层仍需自己推断哪些工具被打断，违背统一事件流设计。

### 4. 回归测试以 mapper 级最小复现为主，补充字段关联与取消覆盖

**Decision**

测试层优先新增 `_EventMapper` 级最小回归用例，直接喂入构造的 `easyharness_tool` started/completed/cancelled 事件，断言输出事件的 `tool_use_id`、`name`、`input`、`text` 与终态顺序。必要时再保留现有 agent.stream 路径测试作为高层补充，但不把核心回归依赖在更重的运行时集成上。

**Rationale**

这个 bug 的最短反馈回路就在 mapper 内部。把测试放在 mapper 级别更容易精准定位，也能避免上层 fake model、线程和取消时序把问题掩盖掉。

**Alternatives considered**

- 只写高层 stream 集成测试：覆盖面更宽，但失败定位更慢，而且更容易被其他运行时噪声干扰。
- 只人工复现不写回归：无法形成长期门禁，不符合这次修复的目标。

## Risks / Trade-offs

- **[风险] 终态事件缺少 `tool_use_id` 时，公共事件的计时信息可能退化为原始终态载荷可提供的信息。**
  - **缓解**: 明确采用“不能串线优先于信息完整”的策略；未匹配时不得窃取其他活动调用的 started 上下文。

- **[风险] 取消路径从单工具终态扩展为多工具终态，可能暴露出某些上层消费者隐含的‘同一时刻最多一个活动工具’假设。**
  - **缓解**: 在 spec 与测试中把多活动工具取消语义写成显式契约，让消费方按真实事件模型收敛。

- **[风险] 活动工具状态如果未在终态时及时移除，会导致后续事件复用旧状态。**
  - **缓解**: 设计上要求所有 terminal path 都按 `tool_use_id` 做一次性 `pop`，并用回归测试覆盖连续多轮 started/terminal 序列。

## Migration Plan

1. 为 `runtime-event-stream` 增加工具身份一致性与多活动取消的规范要求。
2. 调整 `_EventMapper` 的工具阶段状态结构与终态解析逻辑。
3. 补充 mapper 级回归测试，覆盖同名重叠、异名重叠和取消收口。
4. 运行相关测试，确认事件序列与字段绑定符合新契约。
5. 由于没有公开 API 和数据模型迁移，本次发布不需要额外迁移脚本；如需回滚，只需回退 mapper 与测试改动。

## Open Questions

- 当前没有必须阻塞实施的开放问题。
- 若后续要支持更细粒度的异常监控，可以再单独评估是否为“终态未匹配任何活动工具”的情况增加内部诊断钩子；这不属于本次最小闭环。
