## Why

`EasyHarness` 当前已经具备最小 Agent SDK 骨架，但仍要求调用方自行准备文件系统工具，导致本地 coding agent 的开箱可用性偏弱。现在引入基于 `fileglide` 的默认工具集，可以在不破坏极简公开面的前提下，把最常见的文件浏览、检索与精确编辑能力变成稳定的出厂配置。

## What Changes

- 新增 `easyharness.toolset` 子包，用于承载基于 `fileglide` 的官方工具集构建入口与受控导出。
- 新增一组面向 coding agent 的 `fileglide` 工具适配层，把 `fileglide` 的服务能力封装为 EasyHarness `tool` 契约可消费的工具对象。
- 新增默认工具装载机制：`Agent` 在未显式禁用时自动装载官方文件系统工具集，作为本地 agent 的出厂配置。
- 新增安全开关：允许开发者通过 `Agent` 构造参数显式禁用默认文件系统 I/O 工具。
- 明确默认文件系统工具只从 `easyharness.toolset` 导出，不新增根包公开导出，继续保持 `easyharness` 顶层公开面最小化。
- 明确 `fileglide` 结果与异常需要经过 EasyHarness 适配层归一化，确保工具输出满足现有 `ToolOutput` / JSON 可序列化契约。

## Capabilities

### New Capabilities
- `fileglide-toolset`: 定义官方 `fileglide` 工具集的导出边界、默认包含的工具、输出归一化方式，以及 `easyharness.toolset` 子包的公开入口。

### Modified Capabilities
- `agent-sdk-surface`: 调整 `Agent` 的公开构造语义，使其支持默认装载官方文件系统工具集，并允许调用方通过显式参数禁用该默认行为。

## Impact

- 受影响代码主要位于 `easyharness/_internal/runtime.py`、`easyharness/toolset/`、`easyharness/__init__.py` 邻近文档与测试。
- `Agent` 的默认运行行为会发生变化：未禁用时将比当前版本多出一组官方文件系统工具。
- 依赖关系仍建立在现有 `fileglide` 依赖之上，但 SDK 将新增一层官方适配与导出约束。
- README、OpenSpec 规格和 SDK 回归测试需要同步更新，以反映“默认文件工具已成为出厂配置，但仍可显式禁用”的新约定。
