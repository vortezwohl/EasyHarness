## 1. Public Configuration Surface

- [x] 1.1 为 `ModelConfig` 增加可选 `context_window_limit` 字段，并保持最小配置路径仍然只需要 `model` 与 `api_key`
- [x] 1.2 更新公开文档与类型说明，明确 `context_window_limit` 是可选覆盖项，而不是调用方必须提供的 provider 细节

## 2. Runtime Resolution

- [x] 2.1 在 runtime model 构建路径中加入统一的 context window resolution helper，按“显式值 > 已知模型解析 > 最终 fallback 200000”确定结果
- [x] 2.2 为 provider-prefixed model ID 增加归一化查表逻辑，确保类似 `openai/gpt-4.1-mini` 的值不会误落入 fallback
- [x] 2.3 将 resolved `context_window_limit` 显式传入 `LiteLLMModel` 构建路径，避免继续依赖下游 warning fallback

## 3. Verification

- [x] 3.1 补充显式 `context_window_limit` 覆盖测试
- [x] 3.2 补充已知模型自动解析测试，包括 provider-prefixed model ID 场景
- [x] 3.3 补充未知模型统一 fallback 到 `200000` 的测试，并确认 proactive compression 路径不再依赖底层未设置 warning
