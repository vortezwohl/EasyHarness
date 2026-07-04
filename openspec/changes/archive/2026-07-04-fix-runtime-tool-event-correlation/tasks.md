## 1. Event Mapper State Model

- [x] 1.1 将 `_EventMapper` 的单个活动工具槽位改为按 `tool_use_id` 关联的活动工具状态表
- [x] 1.2 调整工具终态收口逻辑，仅在命中相同 `tool_use_id` 时复用 tracked 状态，未命中时退回原始终态载荷
- [x] 1.3 调整取消路径，确保存在多个活动工具阶段时会逐个发出 `tool.cancelled` 后再发出 `system.cancelled`

## 2. Regression Coverage

- [x] 2.1 为 `_EventMapper` 增加同名工具重叠的最小回归测试，断言 `tool_use_id` 序列保持 `tool-1, tool-2, tool-1, tool-2`
- [x] 2.2 为 `_EventMapper` 增加异名工具重叠测试，断言终态事件不会串用其他工具的 `name`、`input` 与输出关联
- [x] 2.3 为取消路径增加多活动工具阶段测试，断言每个活动工具都有自己的 `tool.cancelled` 终态

## 3. Verification

- [x] 3.1 运行 `tests/test_sdk.py` 中与 `_EventMapper`、工具事件和取消相关的定向测试
- [x] 3.2 复查变更后的事件序列是否满足 spec 中的工具身份一致性与取消收口要求
