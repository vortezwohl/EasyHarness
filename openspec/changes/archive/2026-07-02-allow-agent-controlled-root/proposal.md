## Why

当前官方 `fileglide_*` 工具把根目录作用域固定在工具构建时确定的 `root` 上，这让 agent 无法在一次会话内按需访问工作区外部路径。对于需要跨项目读取、检查上级目录配置或临时切换目标根目录的本地 coding agent，这个固定作用域已经从安全边界变成了能力阻塞点。

## What Changes

- 调整官方 `fileglide_*` 工具的调用契约，为相关工具增加可选的 `root` 输入参数，由 agent 在调用时直接提供目标根目录。
- 当调用方显式提供 `root` 时，工具必须直接使用该根目录解析本次请求，不再对该 `root` 施加额外 allowlist、祖先目录或工作区范围限制。
- 保留现有默认行为：未显式提供 `root` 时，工具仍沿用当前已绑定的默认根目录，避免无关调用被迫改写。
- 统一更新工具元数据、README 示例、测试与错误输出约定，使“agent 可自行输入 root”成为清晰稳定的官方能力。

## Capabilities

### New Capabilities
- `fileglide-dynamic-root`: 定义官方 `fileglide_*` 工具如何接受 agent 在调用期提供的 `root`，以及显式 `root` 覆盖默认根目录且不受系统额外限制的行为契约。

### Modified Capabilities
- 无。

## Impact

- 受影响代码主要位于 `easyharness/toolset/fileglide.py`，并可能波及 `fileglide` 适配层所依赖的参数校验与调用辅助函数。
- README 与 SDK 测试需要同步覆盖“默认根目录”和“显式 root 覆盖默认根目录”两条路径。
- 该变更会弱化当前 `fileglide` 默认工具集的作用域安全语义；风险将集中转移到调用方提示与上层运行环境，而不再由 SDK 内部限制路径范围。
