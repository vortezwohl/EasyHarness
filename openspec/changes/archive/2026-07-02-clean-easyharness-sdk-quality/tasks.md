## 1. Baseline And Policy

- [x] 1.1 盘点 `easyharness/` 与 `tests/` 中的 unused import、unused 形参、导入排序、长行、缺失注解和 `type: ignore` 现状，并把需要清理的项与协议性保留项区分开
- [x] 1.2 依据仓库规则确认 Python 文档/注释默认中文、英文例外场景和本次不做“全量改英文”的边界，并同步到实现决策中

## 2. Deterministic Cleanup

- [x] 2.1 清理确定性的低风险噪声：删除未使用 import 与未使用形参，修复导入排序和格式漂移
- [x] 2.2 修复 `easyharness/` 与相关测试中的长行和可格式化 PEP 8 问题，确保不改变 SDK 对外行为
- [x] 2.3 审核不使用 `self`/`cls` 的方法，只对不涉及协议、override、property 或抽象接口的方法做静态化或等价重构

## 3. Type And Editor Warning Tightening

- [x] 3.1 收紧核心 SDK 实现中的明显过宽注解，优先处理无依据的 `Any` 和可直接表达的更精确类型
- [x] 3.2 消除无依据的 `type: ignore`，对必须保留的动态边界只在最小范围内保留弱类型
- [x] 3.3 为关键测试替身和 override 方法补齐足够精确的签名注解，降低 PyCharm/静态检查器的无效 warning

## 4. Verification And Guardrails

- [x] 4.1 运行并通过约定的 `ruff check`、`ruff format --check` 与现有测试，确认清理后行为不变
- [x] 4.2 复查剩余 warning 是否都属于有意保留的兼容性或动态边界，并删除不必要的噪声保留项
