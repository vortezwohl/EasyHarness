## 1. Tool Contract Adjustment

- [x] 1.1 调整 `easyharness._internal.tools.tool()` 的参数元数据校验，允许零参数函数使用空 `parameters` 映射
- [x] 1.2 保持非零参数函数的严格合同校验，确保空 `parameters` 仍会被拒绝

## 2. DeepSeek Runtime Compatibility

- [x] 2.1 在 `easyharness._internal.model` 中加入 DeepSeek V4 的最小识别逻辑，保持非 DeepSeek 默认路径不变
- [x] 2.2 实现一个极薄的 DeepSeek 私有模型适配分支，只覆盖多轮 thinking/tool-call 所需的消息格式化行为
- [x] 2.3 确保 DeepSeek 兼容分支只在需要的 tool-call 连续场景保留必要的 `reasoningContent`，不引入通用 provider 抽象

## 3. Regression Coverage

- [x] 3.1 为零参数工具声明增加最小回归测试，并验证非零参数函数仍需完整参数文档
- [x] 3.2 为 DeepSeek 多轮 reasoning/tool-call 历史格式化增加最小回归测试
- [x] 3.3 运行现有 SDK 回归测试与新增测试，确认默认路径未回退
