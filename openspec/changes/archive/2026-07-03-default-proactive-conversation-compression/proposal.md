## Why

EasyHarness 现在把默认 conversation compression 行为隐式委托给上游 Strands 默认值，这让 SDK 的实际压缩时机和保留策略既不稳定也不透明。既然 EasyHarness 已经提供了自定义的事件化 conversation manager，就应该把默认压缩策略显式收回到 SDK 边界内，并把这套默认行为写进文档与规范。

## What Changes

- 调整默认 `EventingSummarizingConversationManager` 策略，默认开启 `proactive_compression`，而不是仅在上下文溢出后再做 reactive summary。
- 固化 EasyHarness 自己的默认压缩参数：`summary_ratio=0.3`、`preserve_recent_messages=8`。
- 保持 `EventingSummarizingConversationManager` 的显式参数覆盖能力，调用方仍可传入自己的 `summary_ratio`、`preserve_recent_messages`、`proactive_compression` 和其他底层参数。
- 保持 `Agent(..., conversation_manager=custom_manager)` 的透传优先语义，不把 SDK 默认值强加到自定义 manager 上。
- 在 README 中新增默认消息压缩机制说明，明确 proactive 触发、默认比例、默认保留消息数以及可覆盖方式。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `conversation-compression`: 默认 conversation compression 策略将从“仅 reactive overflow recovery”调整为“SDK 默认 proactive compression + 显式默认参数”，并新增对 README 默认行为说明的要求。

## Impact

- 受影响代码主要位于 `easyharness/_internal/conversation.py`，因为默认 manager 的构造默认值将从“跟随上游”改为“由 SDK 明确声明”。
- `Agent` 的默认运行时行为会发生可观察变化：在达到上下文窗口阈值前，可能先触发 proactive summary 并发出 `compress` 事件。
- 测试需要补充默认参数与 proactive compression 事件路径验证，避免未来回退到上游隐式默认值。
- README 需要新增 conversation compression 说明，减少调用方对“为什么还没 overflow 就开始 summary”的困惑。
