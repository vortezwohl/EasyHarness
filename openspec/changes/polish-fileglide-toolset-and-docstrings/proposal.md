## Why

`add-default-fileglide-toolset` 已经把官方 file 工具集引入到 `easyharness.toolset`，但当前实现仍遗留三个会同时影响同一批文件的收尾问题：官方工具名仍是临时性的 `fs_*` 前缀、`easyharness/` 下的 Python 注释与 docstring 仍与用户要求的 en-us 规范和已归档语言策略冲突、以及若干未使用导入和形参尚未完成“真没用 / 协议占位 / 逻辑漂移”的判定。若分开修，会重复改动相同实现、测试与文档，并继续暴露一个不稳定的工具契约。

## What Changes

- **BREAKING** 将官方 fileglide 工具集的公开工具名从 `fs_*` 统一改为 `fileglide_*`，并同步更新默认自动装载行为、测试断言、README 示例与同名覆盖点；不保留双前缀别名。
- 将 `easyharness/` 下 Python 文件头说明、类/函数 docstring 与关键维护注释统一改为 en-us，并修改 OpenSpec 语言策略，使仓库规范与代码实现一致。
- 对 `easyharness/` 与相关测试中的未使用 import、形参和同类静态告警做一次定向审计：真正无用的删除，协议/覆写占位的显式保留；若发现“未使用”源于实现偏离预期逻辑，则先修正逻辑再清理告警。

## Capabilities

### New Capabilities
- `fileglide-tool-naming`: 约束官方 fileglide 工具集的唯一公开命名方案为 `fileglide_*`，并覆盖默认自动装载与同名覆盖场景。

### Modified Capabilities
- `python-language-policy`: 将 EasyHarness Python 注释与 docstring 的默认语言策略从中文改为 en-us，并明确该规则只直接约束维护性文档表面。
- `sdk-code-hygiene`: 强化未使用 import / 形参的治理要求，清理前必须先判断其属于死代码、协议占位，还是实现逻辑漂移。

## Impact

- 受影响代码主要位于 `easyharness/toolset/fileglide.py`、`easyharness/toolset/__init__.py`、`easyharness/_internal/runtime.py` 与 `tests/test_sdk.py`，并会波及 README 中对默认文件工具的示例说明。
- `build_fileglide_tools()` 返回的工具名，以及 `Agent(enable_fileglide=True)` 时默认暴露给模型的工具名，将从 `fs_*` 切换为 `fileglide_*`。
- `easyharness/` 下 Python 源码的文件头说明、docstring 与关键维护注释将整体改为 en-us；运行时字符串是否改动仍以外部契约为准，不做无边界的全仓库翻译。
- 不新增根包导出，也不改变 `easyharness.__all__` 的最小公开面约束。
