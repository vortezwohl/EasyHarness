## Context

`EasyHarness` 当前已经有稳定的 `Agent`、`tool` 契约和最小公开面，但本地 coding agent 仍然缺少一套官方、开箱即用的文件系统工具。仓库已经依赖 `fileglide`，其服务层覆盖文本读取、路径遍历、名称搜索、正则搜索、精确写入、行替换、锚点插入、文件/目录管理和大小检查，能力上足够完整。

直接把 `fileglide` 的底层服务或整棵 CLI 命令树原样暴露给 `Agent` 并不优雅，原因有三点：

- `fileglide` 返回值中包含 `PreviewDetail` 等 dataclass，不能直接满足 EasyHarness 现有工具输出契约。
- `fileglide` 的操作粒度偏底层，若一比一映射为默认工具，工具数量会偏大，增加模型的选择负担。
- 默认装载是公开行为的一部分，需要在不扩大根包公开面的前提下，引入一个官方工具集层。

这次设计需要同时满足以下约束：

- 根包 `easyharness` 仍然只保留现有五个顶层公开名。
- 官方文件工具必须从 `easyharness.toolset` 导出，而不是从根包导出。
- `Agent` 默认自动装载文件系统工具，但开发者必须可以显式禁用。
- 方案应尽量复用 `fileglide` 现有服务与 EasyHarness 现有 `tool` 装饰器，不新增新的注册系统或插件系统。

## Goals / Non-Goals

**Goals:**

- 提供一个官方 `easyharness.toolset` 子包，作为文件系统工具集的唯一公开入口。
- 提供一组适合 coding agent 默认使用的官方文件系统工具，并默认装载到 `Agent`。
- 提供一个显式安全开关，允许开发者禁用默认文件系统 I/O 工具。
- 保持根包顶层公开面和现有 `tool` 契约不变。
- 复用 `fileglide` 的作用域约束、文本编码处理、精确编辑能力和搜索能力。
- 把 `fileglide` 返回值和异常统一归一化为 EasyHarness 可消费的 `ToolOutput`。

**Non-Goals:**

- 不引入新的插件系统、工具注册中心或 profile 配置层。
- 不把 `fileglide` 的所有 CLI 子命令一比一暴露为默认工具。
- 不修改根包 `easyharness.__all__`，也不把 `toolset` 重新导出到根包。
- 不在本次设计中扩展异步工具模型、权限系统或多租户文件作用域模型。

## Decisions

### 1. 使用 `easyharness.toolset` 作为官方工具集子包

**Decision**

新增 `easyharness.toolset` 子包，作为官方文件工具集的唯一导出边界。根包 `easyharness` 不新增任何公开导出，`toolset` 只通过子包路径访问。

建议结构如下：

```text
easyharness/
  __init__.py
  _internal/
    runtime.py
  toolset/
    __init__.py
    fileglide.py
```

其中：

- `easyharness.toolset.fileglide` 负责 `fileglide` 适配、工具定义和工具集构建。
- `easyharness.toolset.__init__` 只做受控导出，不承载实现细节。

**Rationale**

这能把“官方工具集”与“根包最小 SDK 面”清晰分层，避免再次出现 `easyharness.tool` 这类命名冲突，也避免把业务向工具集能力误并入 core SDK 入口。

**Alternatives considered**

- 直接放到根包：最省路径，但会破坏现有顶层公开面约束。
- 放到 `_internal`：不利于开发者显式复用官方工具集。
- 放到独立 `contrib` 包：分层更重，对当前仓库过度设计。

### 2. 默认装载使用“压缩后的官方工具集”，而不是完整命令树

**Decision**

默认装载的官方文件工具集采用“少量高语义工具”设计，而不是 `fileglide` 操作的一比一映射。推荐默认集合为：

- `fs_list_tree`: 列出目录树、文件列表和基础元数据。
- `fs_search_paths`: 按名称、路径或模糊匹配搜索路径。
- `fs_read_text`: 读取全文或指定行范围。
- `fs_search_text`: 对文本内容执行正则搜索。
- `fs_edit_text`: 执行覆盖写入、追加写入、插入写入、行替换和锚点插入。
- `fs_manage_paths`: 执行文件/目录创建、移动、存在性检查，以及带确认语义的删除预览。
- `fs_inspect_path`: 执行大小检查和必要的二进制信息读取。

这些工具内部再分发到 `fileglide` 的 facade/service 层。

**Rationale**

默认装载是给模型直接消费的。工具过多会稀释选择质量，工具过细也会增加提示与 schema 噪声。按“读取 / 搜索 / 编辑 / 管理 / 检查”分组，更符合 coding agent 的高层心智模型。

**Alternatives considered**

- 完整映射 `fileglide` 全部命令：能力最全，但默认工具面过大。
- 只提供只读工具：安全性更高，但不满足“作为出厂配置”的实际开发闭环。
- 提供单一超级工具：参数过重，可读性和可测性都会下降。

### 3. `Agent` 只新增一个显式禁用开关，不承担高级工具配置职责

**Decision**

在 `Agent` 构造参数中新增一个布尔开关，推荐命名为：

- `enable_fileglide: bool = True`

语义为：

- `True`：在调用方未显式禁用时，自动并入官方文件工具集。
- `False`：完全不装载默认文件系统 I/O 工具。

`Agent` 不新增更多与 fileglide 细节绑定的参数。高级定制，例如自定义根目录、自定义工具子集，统一通过 `easyharness.toolset` 显式构建后传入 `tools=[...]` 完成。

**Rationale**

这样可以把 `Agent` 的公开构造面控制在最小增量内，只暴露“是否启用默认文件工具”这个真正属于公开行为的问题，而不把 fileglide 的内部配置细节耦合进 `Agent` API。

**Alternatives considered**

- 使用 `disable_file_tools: bool = False`：能表达安全语义，但双重否定较重。
- 在 `Agent` 上新增 root、include/exclude、tool subset 等参数：灵活但会快速膨胀公开 API。
- 完全不在 `Agent` 上提供开关：无法满足显式安全禁用诉求。

### 4. `fileglide` 结果统一走 Adapter 层归一化

**Decision**

在 `easyharness.toolset.fileglide` 中增加一个明确的适配层，负责：

- 调用 `FileGlideFacade` 或其 service 层。
- 使用 `fileglide.serializers.to_primitive()` 将 dataclass、`Path` 等值归一化为 JSON-safe 结构。
- 将成功结果包装为 `ToolOutput`。
- 将 `FileGlideError` 转换为结构化失败输出，而不是把底层 dataclass/异常直接暴露给 `Agent`。

推荐输出策略：

- `data`: 保留 `{ok, operation, result, error}` 这类结构化负载。
- `model_text`: 给模型的简洁结果摘要。
- `preview`: 给 UI/事件流的短摘要。
- `detail`: 在需要时包含完整归一化结果。

**Rationale**

这一步是适配层存在的核心价值。它既复用了 `fileglide` 的成熟逻辑，又不需要修改 EasyHarness 当前 `tool` 执行主干，就能保证官方工具集输出稳定、可显示、可继续被模型消费。

**Alternatives considered**

- 直接返回 `fileglide` 原始结果：会破坏现有序列化契约。
- 让 `FileGlideError` 直接抛出：会丢失结构化错误细节。
- 修改 EasyHarness 核心工具执行器以原生理解 `fileglide`：侵入面过大，不适合作为首版方案。

### 5. 默认作用域遵循当前工作目录，进一步定制通过显式构建完成

**Decision**

默认装载的官方文件工具集使用当前工作目录作为 `fileglide` root。若调用方需要更严格或不同的作用域，应关闭默认文件工具并显式调用 `easyharness.toolset` 构建自定义工具集。

例如：

```python
from easyharness import Agent
from easyharness.toolset import build_fileglide_tools

agent = Agent(
    model=model,
    system_prompt=prompt,
    enable_fileglide=False,
    tools=build_fileglide_tools(default_root="D:/Projects/PythonProjects/EasyHarness"),
)
```

**Rationale**

把作用域约束交给 `fileglide` 自身处理，可以复用它已有的 root 保护逻辑，同时避免把“默认出厂配置”和“高级安全定制”混成一个构造器。

**Alternatives considered**

- 强制要求 `Agent` 每次都传 root：会损害开箱体验。
- 完全不支持显式 root：会限制嵌入式使用场景。

## Risks / Trade-offs

- **[风险] 默认装载后，`Agent` 的工具面会变大** → 通过压缩为少量高语义工具控制模型选择成本，并保留显式禁用开关。
- **[风险] 写入类工具默认开启会让安全预期变复杂** → 在 `Agent` 上提供显式禁用参数，并让删除类操作继续保留 `fileglide` 的预览/确认语义。
- **[风险] 适配层自行组织错误输出，可能与 EasyHarness 通用异常流不完全一致** → 统一官方 fileglide 工具的错误结构，保持 `data` 字段稳定，避免散落的异常格式。
- **[风险] `toolset` 一旦导出过多构建函数，会逐步滑向工具平台** → 子包只暴露受控入口，默认方案优先于全量原始映射。

## Migration Plan

1. 新增 `easyharness.toolset` 子包与 fileglide 适配层，不触碰根包公开导出。
2. 在 `Agent` 中增加默认文件工具装载逻辑与 `enable_fileglide` 开关。
3. 先补默认工具集与禁用开关的规格和测试，再补 README 示例与行为说明。
4. 更新现有“v1 不提供默认业务工具包”的文档表述，改为“core 根包不导出工具包，但内置官方 file toolset 出厂配置”。
5. 若实现阶段发现默认工具数量仍然过多，优先继续收缩默认集合，而不是追加更多构造参数。

## Open Questions

- 当前无阻塞性开放问题。
- 若实现阶段发现二进制读写工具会显著增加默认风险面，可在不改动总体架构的前提下，把二进制写能力降级为非默认导出。
