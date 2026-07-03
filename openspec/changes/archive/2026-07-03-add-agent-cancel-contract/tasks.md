## 1. Public Cancellation Surface

- [x] 1.1 为公开 `Agent` 和内部 `_StrandsRuntime` 增加 `cancel()` 入口，并保持调用方无需接触内部对象即可取消当前 invocation
- [x] 1.2 复查取消中的 `run()`、`stream()` 和空闲态 `cancel()` 路径，确保取消是幂等的且不会破坏当前会话复用语义

## 2. Event Contract

- [x] 2.1 扩展 `AgentEvent` 的公开状态词汇，加入 `cancelled` 终态并更新相应类型定义
- [x] 2.2 调整 runtime event mapper，把底层取消结果归一化为公开阶段终态和最终 `system.cancelled` 收口事件
- [x] 2.3 复查取消发生在 thinking、assistant、tool 和尚未产生公开阶段 delta 的场景，确保事件序列都满足规范

## 3. Verification And Documentation

- [x] 3.1 补充取消中的 `stream()`、取消中的 `run()`、取消后复用和空闲态 `cancel()` 的最小回归测试
- [x] 3.2 更新 README，说明 `Agent.cancel()` 的使用方式、`cancelled` 事件语义以及 `stream()` 与 `run()` 的职责分层
