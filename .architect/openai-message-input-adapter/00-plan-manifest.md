# Plan Manifest

## Metadata
- Document Type: Plan Manifest
- Document ID: PLAN
- Plan Name: openai-message-input-adapter
- Created At: 2026-07-28:15:36:54.415
- Document Language: zh-CN
- Plan Digest: 1431a3f9605982ed0032080c938eecef4b8ff97ca70636e987708ce0dd359c49

## Objective
在 EasyHarness 的公开 `Agent.run()` 与 `Agent.stream()` 边界支持 `str | list[dict]`；两种输入都必须先规范化为 Strands `Messages`，再传给底层运行时。

## Non-Goals
- 不支持 OpenAI Responses API 事件、多模态 content parts、旧式 `function` 调用或 provider 专有 reasoning 字段。
- 不替换 Agent 既有会话历史，不执行调用方提供的历史工具调用，不改变系统提示。

## Approved Design Bundle
- D-001-openai-message-input-adapter，已由用户在 2026-07-28 显式调用 `architect-propose` 形成批准证据。
- 核心决策：以严格的私有 Adapter 统一转换字符串和 OpenAI Chat Completions 文本/function-tool 历史；拒绝 `system` 与 `developer`。

## Architect Build Entry Conditions
- 必须保持字符串调用、会话追加、构造期 `system_prompt`、工具 Context、取消、压缩、事件、懒惰 stream 与互斥锁语义。
- 仅允许执行 T-001、T-002；若实现需要跨越 D-001 的停机条件，必须停止并按任务冲突协议请求用户决策。
