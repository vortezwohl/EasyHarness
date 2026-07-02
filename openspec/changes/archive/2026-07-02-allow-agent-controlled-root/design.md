## Context

当前官方 `fileglide_*` 工具在构建阶段就把 `root` 固定下来，后续每次调用只能在该作用域内工作。这个设计把路径边界交给 SDK 决定，适合保守默认值，但不适合本地 coding agent 在一次会话里按需读取兄弟项目、上级目录配置或临时指定新的根目录。

这次需求很直接：让 agent 自己输入 `root`，系统不再额外限制该 `root` 的取值范围。与此同时，用户要求方案尽量最小、优雅，不引入新的全局状态、配置层或额外工具。

## Goals / Non-Goals

**Goals:**

- 允许 agent 在调用官方 `fileglide_*` 工具时显式提供 `root`。
- 显式 `root` 一旦提供，即直接作为本次调用的解析根目录，不再经过 SDK 自己的 allowlist 或工作区范围限制。
- 保留现有默认行为，使未传 `root` 的调用继续使用工具构建时绑定的默认根目录。
- 将改动收敛在 `easyharness.toolset.fileglide` 适配层、工具元数据和对应测试中。

**Non-Goals:**

- 不新增 `Agent` 构造参数。
- 不新增“切换 root”“记住当前 root”之类的状态型工具。
- 不修改 `fileglide` 上游库的作用域服务实现。
- 不为任意路径访问再增加新的安全保护层。

## Decisions

### 1. 采用“每次调用可选传入 `root`”而不是新增状态型 root 工具

**Decision**

为所有官方 `fileglide_*` 工具增加可选参数 `root: str | None = None`。同时将公开 builder 参数命名明确为 `default_root`。当调用未传 `root` 时，继续使用 builder 绑定的默认根目录；当调用传入 `root` 时，本次调用改用该 `root`。

**Rationale**

这是满足需求的最小改动：

- 不改 `Agent` 公开面。
- 不需要会话级共享状态，也不需要新增 `fileglide_set_root()` 之类的状态同步逻辑。
- 工具调用记录天然包含 `root`，便于测试和审计。

**Alternatives considered**

- 新增 `Agent(root=...)` 或类似构造参数：不满足“agent 自己输入 root”，而且会扩大公开 API。
- 新增 `fileglide_set_root()`：会把文件工具变成有状态协议，增加调用顺序耦合和调试复杂度。
- 直接取消所有 root 概念：会让现有相对路径语义和 `fileglide` 服务层接口一起漂移，改动面过大。

### 2. SDK 不再限制显式 `root` 的取值，但仍把它作为本次调用的作用域根

**Decision**

SDK 对调用方显式提供的 `root` 只做路径规范化，不做 allowlist、祖先目录、工作区边界或“必须位于默认 root 内”的校验。规范化后的 `root` 直接传给底层 `fileglide` 服务，作为本次调用的解析根目录。

**Rationale**

用户要求的是“agent 自己输入 root，系统不做限制”。最直接的实现就是把“限制 root 能填什么”从 SDK 中删掉，而不是增加另一套宽松策略。这样行为简单、可预期，也不会引入新的判定歧义。

**Alternatives considered**

- 只允许显式 `root` 指向默认 root 的祖先目录：仍然是系统限制，不符合本次要求。
- 只允许在预注册 roots 中切换：更安全，但不是“系统不做限制”的语义。
- 传入 `root` 后仍要求目标路径必须落在默认 root 内：与显式覆盖 root 的目的冲突。

### 3. 作用域错误保留为“相对显式 `root` 的一致性错误”，而不是“系统限制”

**Decision**

当显式 `root` 已提供时，工具仍允许 `fileglide` 基于该 `root` 解析相对路径，并在目标路径逃离该 `root` 时返回结构化 `scope_violation`。这代表“本次调用的输入不一致”，而不是 SDK 对 `root` 的额外限制。

**Rationale**

如果完全取消“目标路径必须相对某个 root 一致”的约束，就需要重写现有服务层的路径解析模型，已经超出最小方案。保留 `fileglide` 现有语义，可以在不改上游库的前提下完成需求，同时维持相对路径、绝对路径和结构化错误的稳定性。

**Alternatives considered**

- 为显式 `root` 新增完全无作用域的裸路径模式：需要分叉现有调用路径，复杂度明显上升。
- 遇到绝对路径时忽略 `root`：会让同一工具同时存在两套解析规则，降低可预测性。

### 4. 只在适配层收口实现，避免扩散到 `Agent` 和核心运行时

**Decision**

改动集中在 `easyharness.toolset.fileglide`：

- 为每个官方工具补充 `root` 参数和元数据说明。
- 提炼一个根据调用期 `root` 解析 `effective_root` 的辅助逻辑。
- 保持 `ToolOutput` 成功/失败结构不变，仅让 `data.root` 反映本次实际生效的根目录。

**Rationale**

这能把 diff 限制在单一模块和测试内，不影响 `Agent` 默认装载逻辑，也不需要触碰 `_internal/runtime.py` 的公开行为。

**Alternatives considered**

- 在运行时层统一拦截并注入 root：职责不匹配，而且无法表达单次调用覆盖。
- 修改上游 `fileglide` facade 默认行为：侵入外部依赖，不适合作为本仓库最小方案。

## Risks / Trade-offs

- **[风险] 默认工具集的安全边界被弱化** → 在设计与文档中明确：显式 `root` 是无约束覆盖，风险由调用方和运行环境承担。
- **[风险] 工具签名统一新增 `root` 会增加模型参数面** → 只新增一个可选参数，并保持其他契约不变，避免再引入状态工具或额外配置对象。
- **[风险] 用户可能误以为“无系统限制”意味着目标路径也完全不受 `root` 约束** → 在工具说明、README 和 spec 中明确：系统不限制 `root` 的取值，但本次调用仍以该 `root` 作为解析基准。
- **[风险] 现有 scoped 测试需要改写** → 拆分为“默认 root 仍受限”和“显式 root 可覆盖默认 root”两类测试，保持回归定位清晰。

## Migration Plan

1. 更新 `proposal` 对应 spec，确定显式 `root` 覆盖默认 root 的规范行为。
2. 在 `easyharness.toolset.fileglide` 中为七个官方工具增加可选 `root` 参数，并统一接入 `effective_root` 解析逻辑。
3. 更新工具元数据与 README 示例，展示默认调用和显式 root 调用两条路径。
4. 调整 SDK 测试，覆盖默认行为、显式 root 覆盖、结构化错误输出。
5. 若验证通过，则无需迁移运行时入口；现有调用保持兼容。

## Open Questions

- 当前无阻塞性开放问题。
