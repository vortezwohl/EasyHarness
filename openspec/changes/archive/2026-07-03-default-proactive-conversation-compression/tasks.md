## 1. Default Compression Policy

- [x] 1.1 调整 `EventingSummarizingConversationManager` 的默认构造参数，显式固定 `proactive_compression={"compression_threshold": 0.7}`、`summary_ratio=0.3`、`preserve_recent_messages=8`
- [x] 1.2 保持默认 manager 的显式参数覆盖能力，并确保其余上游构造参数仍可透传到底层 `SummarizingConversationManager`
- [x] 1.3 复查 `Agent` 默认路径与 `conversation_manager` 自定义路径，确保 SDK 默认值只作用于未传入自定义 manager 的场景

## 2. Verification

- [x] 2.1 补充默认 manager 构造默认值验证，覆盖 proactive threshold、`summary_ratio` 和 `preserve_recent_messages`
- [x] 2.2 补充默认 proactive compression 事件路径验证，确保在非 overflow 场景也能发出 `compress` 事件
- [x] 2.3 补充显式覆盖验证，确保调用方传入 `proactive_compression=None` 或自定义 retention 参数时覆盖 SDK 默认值

## 3. Documentation

- [x] 3.1 在 README 中新增 conversation compression 说明，明确默认 proactive 策略、`70%` 阈值、`summary_ratio=0.3` 和 `preserve_recent_messages=8`
- [x] 3.2 在 README 中说明 `compress` 事件与默认压缩机制的关系，以及如何通过显式 manager 参数或自定义 `conversation_manager` 覆盖默认策略
