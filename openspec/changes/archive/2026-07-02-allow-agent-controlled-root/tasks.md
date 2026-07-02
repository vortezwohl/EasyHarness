## 1. Tool Contract Updates

- [x] 1.1 为七个官方 `fileglide_*` 工具补充可选 `root` 参数，并同步更新工具元数据说明
- [x] 1.2 在 `easyharness.toolset.fileglide` 中提炼调用期 `effective_root` 解析逻辑，确保显式 `root` 覆盖默认根目录
- [x] 1.3 保持 `ToolOutput` 成功与失败结构不变，并让 `data.root` 反映本次实际生效的根目录

## 2. Verification Coverage

- [x] 2.1 调整现有 scoped 测试，验证未传 `root` 时仍沿用默认根目录
- [x] 2.2 新增显式 `root` 覆盖测试，验证工具可访问默认根目录之外或其上级目录下的目标路径
- [x] 2.3 新增显式 `root` 模式下的失败测试，验证结构化错误与 `scope_violation` 行为保持稳定

## 3. Docs and Apply Readiness

- [x] 3.1 更新 README 示例，展示默认调用与显式 `root` 调用两条路径
- [x] 3.2 运行定向测试并记录结果，确认动态 `root` 契约已满足 proposal、design 与 spec 要求
