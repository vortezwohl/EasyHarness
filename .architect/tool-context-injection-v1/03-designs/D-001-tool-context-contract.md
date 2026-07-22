# Design: D-001-tool-context-contract

## Metadata
- Document Type: Design
- Document ID: D-001
- Plan Name: tool-context-injection-v1
- Created At: 2026-07-22:13:35:47.206
- Document Language: zh-CN

## Concept
- Canonical Name: `ToolContext` 标记基类与注解驱动的隐藏参数识别
- Category: Public contract / type-driven dependency injection
- Reference: EasyHarness 严格工具定义契约

## Intent
为工具提供可选、可多参数、按回合注入的 Context 入口，且 Context 不属于模型可调用参数。

## Stable Core and Variation
稳定核心是函数签名、metadata 和普通 Pydantic 校验；真实变化是部分参数属于宿主依赖而非 LLM 输入，名称仍由函数签名唯一确定。

## Repository Evidence
`_EasyHarnessTool` 保存 callable 和 signature；`_build_input_model()` 当前把全部参数当作模型输入。零参数工具已经允许 `parameters={}`，Context-only 工具可复用该语义。

## Compatibility Boundary
无 `ToolContext` 注解的工具不变，普通参数 metadata 仍严格校验。Context 参数不再要求 metadata，且禁止出现在 metadata。`ToolContext` 是增量公开导出。

## Pattern Decision
- Candidate: Direct design
- Category: Type-driven parameter classification
- Repository seam: 工具定义期参数分流
- Stable core: Python 签名和 schema 构建
- Real variation: LLM 输入或宿主依赖
- Why it fits: 只有参数分类，没有算法族或对象创建问题。
- Simpler direct design considered: `context_parameter=ctx`；拒绝，重复签名并会随重命名漂移。
- Neighbor patterns rejected: Strategy、Factory Method、Proxy 不适合单一注解分类。
- Misuse risk if forced: registry/factory/container 会过度抽象。
- Verification seam: schema、metadata、Context-only、多 Context。

## External Evidence Decision
接受调用边界显式依赖而非全局状态的原则；不复制外部框架，不为 marker 创建 Factory 或 Strategy。

## Rationale
`ToolContext` 是空 marker class，不是 dataclass。子类可为 frozen dataclass、普通 class 或资源对象；SDK 不构造、不序列化、不持有它。识别 `ToolContext` 子类以及其中基础类型为该子类的 `Optional[T]` / `T | None`，并按签名顺序保存规格。

## Alternatives
- 字符串 `context_parameter=`：拒绝，双重配置。
- 默认值/参数名启发式：拒绝，会误伤普通可选参数。
- `ContextVar` 或全局状态：拒绝，流式与异步边界存在串值风险。
- dataclass 基类：拒绝，错误绑定领域构造和数据语义。

## Functional Boundary
- 目标功能：识别 Context 并从 schema/metadata 对齐中排除。
- 保护功能：普通校验、严格 metadata、零参数工具、直接 Python 调用。
- 非目标：自动创建、DI 容器、序列化、持久化、权限模型。
- 硬停止条件：不得要求存量工具增加虚假参数，且不得改变无 Context 工具 schema。

## Code Impact Scope
`easyharness/_internal/types.py`、`easyharness/_internal/tools.py`、`easyharness/__init__.py`、`tests/test_sdk.py`、`README.md`、`openspec/specs/tool-definition-contract/spec.md`。

## Verification Seams
schema 不含 Context；metadata 含 Context 时失败；普通缺 metadata 仍失败；Context-only 可注册；多 Context 隐藏；非子类不误隐藏。

## Counterexamples
`limit: int = 10` 是普通输入；`scope: dict[str, str]` 和 `scope: object` 不可隐藏。

## Anti-Patterns
按名称/默认值猜测；允许 Context 在 metadata；SDK 实例化 Context；字符串代替类型信息。

## Rules

### MUST DO
- R-D001-001: 只识别 `ToolContext` 或子类和合法可空联合。
- R-D001-002: 按签名顺序保存规格，并让 `parameters` 精确匹配普通模型输入。

### MUST NOT DO
- R-D001-N001: 不得在 schema、描述或模型消息暴露 Context。
- R-D001-N002: 不得以名称、默认值或 dict 等启发式识别，也不得加入 Context 生命周期语义。
- R-D001-001: Only ToolContext subtype annotations are hidden from model metadata and schema.
- R-D001-002: Parameters metadata exactly matches ordinary model input names.
