## Why

EasyHarness 现在默认启用了 proactive conversation compression，但运行时并没有稳定地为底层模型提供 `context_window_limit` 元数据。这会带来两个直接问题：一是 Strands 只能回退到通用默认值并打印警告，二是 proactive compression 的触发时机可能偏离真实模型窗口。继续把这个缺口留给调用方各自猜测，会让 SDK 在一个本该稳定的基础能力上既不安静也不准确。

现在补齐这块边界是合适的，因为 EasyHarness 已经明确拥有自己的 conversation compression 默认策略。既然 SDK 要对 proactive compression 的体验负责，就不能再把上下文窗口容量的解析责任留在隐式 fallback 上。

## What Changes

- 为公开 `ModelConfig` 增加可选的 `context_window_limit` 字段，允许调用方在已知模型窗口时显式覆盖。
- 在 runtime 模型构建路径中增加上下文窗口解析逻辑，按“显式值优先、已知模型表解析其次、最终兜底默认值最后”的顺序确定 `context_window_limit`。
- 统一处理带 provider 前缀的模型 ID，例如 `openai/gpt-4.1-mini`，避免已知模型因为前缀格式差异而错误落入兜底值。
- 让 EasyHarness 在 `LiteLLMModel` 路径上显式设置 resolved `context_window_limit`，避免底层 proactive compression 每次自行退回粗略默认值并打印噪音警告。
- 保持当前 SDK 的直接参数风格，不引入新的 provider profile、模型元数据注册中心或环境变量解析层。

## Capabilities

### New Capabilities

- `context-window-resolution`: 定义 SDK 如何解析模型上下文窗口大小，包括显式覆盖、已知模型查表、provider 前缀归一化和最终兜底值。

### Modified Capabilities

- `model-configuration`: `ModelConfig` 的公开参数集合将新增可选 `context_window_limit`，并把该参数纳入标准直接配置路径。

## Impact

- 受影响代码主要位于 `easyharness/_internal/types.py` 和 `easyharness/_internal/model.py`，因为这次变更涉及公开配置模型和 runtime 模型构建逻辑。
- 测试需要补充三类验证：显式传入 `context_window_limit`、已知模型自动解析、未知模型回退到统一默认值。
- 文档需要说明 `context_window_limit` 的职责边界：它是可选覆盖项，不是调用方必须理解的 provider-specific 复杂配置。
- 这次变更不会新增第三方依赖，也不会引入新的公开入口；变化集中在现有 `ModelConfig` 和 runtime metadata 解析行为上。
