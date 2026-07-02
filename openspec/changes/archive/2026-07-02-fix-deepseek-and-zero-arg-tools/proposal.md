## Why

`EasyHarness` 当前已经具备最小可用的 agent loop SDK 表面，但真实运行暴露出两个会直接影响可用性的缺口：一是 `@tool` 合同错误地拒绝零参数工具，二是基于 `LiteLLMModel` 的 DeepSeek V4 多轮 thinking/tool-call 路径会落入 OpenAI 兼容格式化分支，导致 `reasoningContent` 被错误警告或过滤。现在修这两个问题是合适的，因为它们都属于核心运行时边界错误，继续拖会让 SDK 示例之外的真实接入方持续踩坑。

## What Changes

- 允许 `@tool` 装饰器定义零参数工具；当函数签名为空时，允许 `parameters={}` 作为合法元数据输入。
- 保持工具合同的严格性：只放开“零参数函数 + 空参数文档映射”这一种场景，非零参数函数仍必须让 `parameters` 与签名完全一致。
- 为 DeepSeek V4 提供最小定向兼容路径，在保留现有 `LiteLLMModel` 主体结构的前提下，避免多轮 tool-call 场景错误复用 OpenAI Chat Completions 的 `reasoningContent` 过滤逻辑。
- 在 DeepSeek 定向路径中，仅对需要保留 reasoning 上下文的多轮 tool-call 场景保留必要的 `reasoningContent`，不把该兼容逻辑泛化成新的 provider registry 或配置层。
- 为零参数工具与 DeepSeek reasoning/tool-call 兼容补充最小回归验证。
- 明确本次不处理示例脚本中基于当前工作目录读取 `README.md` 的相对路径问题。

## Capabilities

### New Capabilities
- `zero-arg-tool-support`: 定义零参数工具在严格 `@tool` 合同下的合法声明方式与校验边界。
- `deepseek-thinking-tool-compat`: 定义 DeepSeek V4 多轮 thinking/tool-call 场景下的最小消息格式化兼容行为。

### Modified Capabilities
- None.

## Impact

- 受影响代码主要位于 `easyharness/_internal/tools.py` 与 `easyharness/_internal/model.py`，并可能新增一个极薄的 DeepSeek 定向模型适配实现。
- 受影响测试主要位于 SDK 回归测试，用于覆盖零参数工具声明与 DeepSeek reasoning/tool-call 历史格式化。
- 对外公开 API 不新增名字，也不引入新的 provider registry、环境变量约定或配置层。
