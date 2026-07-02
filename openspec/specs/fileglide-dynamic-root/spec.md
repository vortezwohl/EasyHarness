# fileglide-dynamic-root Specification

## Purpose
TBD - created by archiving change allow-agent-controlled-root. Update Purpose after archive.
## Requirements
### Requirement: 官方 fileglide 工具 MUST 支持调用期显式 `root` 输入
官方 `fileglide_*` 工具 MUST 在其公开调用契约中提供可选的 `root` 参数。`build_fileglide_tools` MUST 使用 `default_root` 作为公开 builder 参数名。调用方未提供 `root` 时，工具 MUST 继续使用构建阶段绑定的默认根目录；调用方提供 `root` 时，工具 MUST 改用该 `root` 作为本次调用的生效根目录。

#### Scenario: 未提供 root 时沿用默认根目录
- **WHEN** 调用方执行任一官方 `fileglide_*` 工具且未传入 `root`
- **THEN** 工具 MUST 使用构建工具集时绑定的默认根目录

#### Scenario: 提供 root 时覆盖默认根目录
- **WHEN** 调用方执行任一官方 `fileglide_*` 工具并显式传入 `root`
- **THEN** 工具 MUST 使用该 `root` 作为本次调用的生效根目录

### Requirement: SDK MUST NOT 对显式 `root` 施加额外范围限制
当调用方显式提供 `root` 时，EasyHarness SDK MUST 只对该路径做规范化处理，MUST NOT 再对其施加 allowlist、工作区边界、默认根目录子路径或祖先目录限制。

#### Scenario: 显式 root 指向默认根目录之外的路径
- **WHEN** 调用方为官方 `fileglide_*` 工具传入一个不位于默认根目录内的 `root`
- **THEN** SDK MUST 接受该 `root` 并继续执行本次调用

#### Scenario: 显式 root 指向上级目录
- **WHEN** 调用方为官方 `fileglide_*` 工具传入默认根目录的上级目录作为 `root`
- **THEN** SDK MUST 接受该 `root` 并基于它解析目标路径

### Requirement: 显式 `root` 调用 MUST 保持现有结构化输出契约
官方 `fileglide_*` 工具在使用显式 `root` 时 MUST 继续返回与现有工具一致的 `ToolOutput` 结构。成功结果中的 `data.root` MUST 反映本次实际生效的根目录；失败结果 MUST 继续保留结构化错误信息。

#### Scenario: 成功结果暴露实际生效的 root
- **WHEN** 官方 `fileglide_*` 工具在显式 `root` 模式下成功执行
- **THEN** 返回结果中的 `data.root` MUST 等于本次调用实际使用的根目录

#### Scenario: 失败结果仍保持结构化错误
- **WHEN** 官方 `fileglide_*` 工具在显式 `root` 模式下执行失败
- **THEN** 返回结果 MUST 继续保留结构化的错误码、消息、细节与路径字段

### Requirement: 显式 `root` 模式 MUST 继续以该 root 作为本次调用的解析基准
官方 `fileglide_*` 工具在显式 `root` 模式下 MUST 仍以该 `root` 作为本次调用的解析基准。若目标路径相对该 `root` 发生逃逸，工具 MUST 返回结构化 `scope_violation`，而不是静默改写为其他路径。

#### Scenario: 相对显式 root 的目标路径发生逃逸
- **WHEN** 调用方传入显式 `root`，且目标路径解析后逃离该 `root`
- **THEN** 工具 MUST 返回结构化 `scope_violation` 错误

#### Scenario: 目标路径位于显式 root 内
- **WHEN** 调用方传入显式 `root`，且目标路径位于该 `root` 内
- **THEN** 工具 MUST 正常执行对应的文件操作

