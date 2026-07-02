## Context

当前分支已经引入 `easyharness.toolset` 与默认 fileglide 工具自动装载能力，但新工具集仍使用临时性的 `fs_*` 名称；这与用户明确要求的 `fileglide_` 官方前缀不一致，也会让 README、测试和默认工具覆盖点继续围绕错误契约编写。与此同时，`easyharness/` 下仍存在中文 Python 注释/docstring，而已归档的 `python-language-policy` 还把中文设为默认，这与本次用户明确要求的 en-us 维护语言直接冲突。

静态审计还暴露出两类不同性质的问题：一类是真正的死符号，例如 `easyharness/toolset/fileglide.py` 中未使用的 `Iterable` 导入与 `_run_fileglide(..., facade=...)` 的无效形参；另一类是为了兼容协议、覆写签名或上游接口而保留的占位参数，例如若干 `**kwargs`。本次方案需要把这两类情况正式区分开，避免把“消告警”错误地变成“删逻辑”。

## Goals / Non-Goals

**Goals:**

- 把官方 fileglide 工具的唯一公开命名方案稳定为 `fileglide_*`，并让默认自动装载与显式同名覆盖都遵循该命名。
- 让 `easyharness/` 下的 Python 文件头说明、docstring 与关键维护注释统一使用 en-us。
- 对未使用 import / 形参做成因审计：删除死代码、保留必要占位、修复因逻辑偏移导致的“假未使用”。
- 保持 `easyharness.toolset` 作为工具集唯一公开导出边界，不扩张根包公开面。

**Non-Goals:**

- 不新增新的工具注册系统、兼容层或 profile 配置层。
- 不为 `fs_*` 保留长期双名别名，也不同时暴露两套官方命名。
- 不做与当前问题无关的仓库级语言翻译；本次只治理 `easyharness/` Python 维护性文本与受影响测试/文档。
- 不修改 `easyharness.__all__`，也不把工具集重新导出到根包。

## Decisions

### 1. 官方工具名一次性改为 `fileglide_*`，不保留 `fs_*` 别名

**Decision**

将 `build_fileglide_tools()` 返回的七个官方工具，以及 `Agent` 默认自动装载暴露出的同名工具，全部统一改为：

- `fileglide_list_tree`
- `fileglide_search_paths`
- `fileglide_read_text`
- `fileglide_search_text`
- `fileglide_edit_text`
- `fileglide_manage_paths`
- `fileglide_inspect_path`

不额外保留 `fs_*` 平行别名，也不在默认工具集中同时放入两套名称。

**Rationale**

这组工具是直接暴露给模型和调用方的官方契约。若同时保留 `fs_*` 与 `fileglide_*`，会扩大默认工具面、制造语义重复，并增加模型选错工具或调用方误判官方名称的概率。由于这套能力仍处于未归档收尾阶段，一次性修正命名比引入兼容层更干净。

**Alternatives considered**

- 保留 `fs_*` 兼容别名：短期兼容性更好，但会让默认工具面翻倍，不适合作为模型默认工具集。
- 延后到后续改动再重命名：会让错误命名继续扩散到更多实现、测试和文档。

### 2. en-us 规则只直接约束维护性文档表面；官方 fileglide 工具元数据同步改为英文

**Decision**

`easyharness/` 下 Python 文件头说明、类/函数 docstring 与关键维护注释统一使用 en-us。与此同时，`easyharness/toolset/fileglide.py` 中直接暴露给模型的官方工具 `purpose`、`when_to_use`、参数说明和返回说明也同步改为英文，使工具名、工具说明和模型消费体验保持一致。

其他运行时字符串是否改动，仍按其外部契约判断：

- 若字符串是模型可见工具契约的一部分，可以改为英文并与工具命名保持一致。
- 若字符串属于协议字段、结构化错误码、现有测试特意校验的输出或其他外部边界，则只在契约允许时改动，不做“为了统一语言而统一语言”的扩散翻译。

**Rationale**

用户要求只明确覆盖注释/docstring，但当前 fileglide 工具元数据同样属于新引入的模型消费契约。如果工具名变成 `fileglide_*`，而说明文字仍保持中文，会形成新的混合契约；同步转英文更一致，也更贴合官方工具集定位。

**Alternatives considered**

- 只改注释/docstring，不改工具元数据：范围更小，但模型看到的是中英混合契约。
- 全仓库所有运行时字符串一并改英文：改动面过大，且会误伤不需要变化的外部契约。

### 3. 未使用符号必须先分类，再决定删除、保留还是修逻辑

**Decision**

对 `easyharness/` 与相关测试里出现的未使用 import、形参和同类静态告警采用三分策略：

- **死代码**：直接删除，例如当前已确认的 `Iterable` 导入与 `_run_fileglide` 的无效 `facade` 形参。
- **协议占位**：若参数存在是为了满足 `Protocol`、覆写签名、动态回调接口或上游约束，则保留，并用代码结构显式体现其意图。
- **逻辑漂移**：若“未使用”暴露的是实现漏接线、行为已偏离预期或本应消费但未消费的状态，则优先修正逻辑，不允许只靠删除符号消告警。

**Rationale**

“未使用”只是表象，不是结论。直接批量删掉未使用符号，很容易把兼容性占位和真实 bug 混在一起，最终留下更隐蔽的行为错误。

**Alternatives considered**

- 机械删除所有未使用符号：最快，但风险最高。
- 统一保留并忽略告警：不会误删逻辑，但会持续积累噪音，违背当前清理目标。

### 4. 验证以定向测试加静态检查为主，不扩大到无关模块

**Decision**

实现阶段优先执行以下验证：

- 针对 `tests/test_sdk.py` 的定向测试，覆盖默认 fileglide 工具名、显式禁用、同名覆盖、作用域保护与结构化输出。
- 对变更过的 `easyharness/` 与测试文件运行静态检查，确认没有新增未使用符号、格式漂移或导入顺序问题。
- 人工复核 README 与 OpenSpec 中的公开示例名称，确认不再引用 `fs_*`。

**Rationale**

本次改动是跨实现、测试和文档的收尾治理，但风险集中在少数模块与公开契约上。使用定向验证能覆盖真实回归点，同时避免把无关模块拖入本次闭环。

**Alternatives considered**

- 只跑单元测试不做静态检查：无法验证“unused symbol triage”目标是否真的完成。
- 全仓库大范围验证：成本高，且与本次精确修改边界不匹配。

## Risks / Trade-offs

- **[Risk] `fileglide_*` 重命名会影响当前分支上已写死 `fs_*` 的调用方** -> 同步更新 README、测试与默认覆盖点，并明确不保留双名别名，避免长期模糊契约。
- **[Risk] en-us 转换可能误改外部契约字符串** -> 仅对维护性文本强制转换；运行时字符串先判断是否属于模型/协议边界，再决定是否调整。
- **[Risk] 清理未使用符号时误删协议占位或真实逻辑** -> 先分类，再改动；对保留项给出明确理由，对疑似逻辑漂移项补行为验证。

## Migration Plan

1. 更新 OpenSpec proposal/design/spec/tasks，明确命名、语言策略与 unused symbol triage 的正式要求。
2. 在 `easyharness/toolset/fileglide.py` 与 `easyharness/_internal/runtime.py` 中完成 `fs_*` 到 `fileglide_*` 的公开契约重命名，并同步调整默认覆盖逻辑。
3. 将 `easyharness/` 下受影响 Python 文件的文件头说明、docstring、关键维护注释与官方 fileglide 工具元数据改为 en-us。
4. 审计并清理未使用 import / 形参；仅对协议占位保留例外，对逻辑漂移项补修正。
5. 更新 `tests/test_sdk.py`、README 与相关 OpenSpec 引用，然后执行定向测试与静态检查。

## Open Questions

- 当前没有阻塞性开放问题。
- 若后续确实出现必须兼容 `fs_*` 的外部消费者，应单独提出一个兼容性 change，而不是在本次默认工具面中保留双名。
