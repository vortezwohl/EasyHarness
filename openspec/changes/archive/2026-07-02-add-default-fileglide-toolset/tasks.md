## 1. Toolset Package Structure

- [x] 1.1 在 `easyharness/toolset/` 下建立官方导出结构，明确 `__init__.py` 与 `fileglide.py` 的职责边界
- [x] 1.2 在 `easyharness.toolset` 中实现 `build_fileglide_tools` 公开入口，并保持根包顶层公开面不变
- [x] 1.3 为 `build_fileglide_tools` 增加显式 `root` 作用域支持，并定义默认作用域行为

## 2. FileGlide Tool Adapters

- [x] 2.1 基于 `fileglide` facade/service 封装官方工具集合：`fs_list_tree`、`fs_search_paths`、`fs_read_text`、`fs_search_text`、`fs_edit_text`、`fs_manage_paths`、`fs_inspect_path`
- [x] 2.2 实现 fileglide 成功结果归一化逻辑，确保 dataclass、`Path` 等值统一转成 JSON 可序列化结构
- [x] 2.3 实现 fileglide 领域错误归一化逻辑，保留错误码、消息、细节与路径，并包装为 EasyHarness 可消费的 `ToolOutput`
- [x] 2.4 为写入、删除、移动等高风险操作补充清晰的工具说明文本，明确预览、确认和失败语义

## 3. Agent Default Loading

- [x] 3.1 在 `Agent` 构造入口增加 `enable_fileglide` 开关，默认启用官方文件工具集
- [x] 3.2 实现默认工具与显式传入工具的合并逻辑，并在同名冲突时让调用方显式工具优先
- [x] 3.3 在 `enable_fileglide=False` 时完全禁用默认文件工具自动装载

## 4. Verification

- [x] 4.1 补充 `easyharness.toolset` 导出边界测试，验证 `build_fileglide_tools` 可导入且根包顶层公开面不扩张
- [x] 4.2 补充默认工具集测试，验证默认构建结果包含约定的官方工具名与作用域行为
- [x] 4.3 补充 `Agent` 默认装载测试，验证默认启用、显式禁用和同名覆盖三种场景
- [x] 4.4 补充 fileglide 结果与错误归一化测试，验证成功结果 JSON-safe、作用域错误结构化、写入类工具行为可观测

## 5. Documentation

- [x] 5.1 更新 README quickstart，说明默认文件工具已作为出厂配置自动装载
- [x] 5.2 增加 `easyharness.toolset` 的显式使用示例，展示自定义 root 与禁用默认文件工具的组合用法
- [x] 5.3 更新相关说明，删除或修正文档中“v1 不提供默认业务工具包”的过时表述
