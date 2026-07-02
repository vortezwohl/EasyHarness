## 1. Public SDK Surface

- [x] 1.1 建立 `easyharness` 的公开模块结构，只对外导出 `Agent`、`ModelConfig`、`AgentEvent`、`ToolOutput` 和 `tool`
- [x] 1.2 建立内部模块边界，把 runtime bridge、tool contract、validator、conversation manager 适配层收敛到私有实现目录
- [x] 1.3 为公开导出边界补充最小验证，确保普通使用路径不需要接触 registry、bridge 或内部合同对象

## 2. Model Configuration

- [x] 2.1 实现 `ModelConfig` 数据结构，支持 `model`、`api_key`、`base_url`、`temperature`、`top_p`、`seed`
- [x] 2.2 实现 `ModelConfig` 默认值逻辑，固定 `base_url=https://api.openai.com/v1`、`temperature=0.01`、`top_p=0.01`、`seed=None`
- [x] 2.3 实现底层模型适配逻辑，确保运行时只依赖显式传参，不读取环境变量或 channel/profile 配置
- [x] 2.4 为默认值与 `base_url` 覆盖行为补充验证

## 3. Tool Definition Contract

- [x] 3.1 实现公开 `tool` 装饰器，要求完整填写 `name`、`purpose`、`when_to_use`、`parameters`、`returns`、`common_failures`
- [x] 3.2 实现基于函数签名和类型注解的参数校验与 schema 推导
- [x] 3.3 实现 `ToolOutput` 公开结构，并支持普通工具返回 `str`、可序列化结果或 `ToolOutput`
- [x] 3.4 为工具元数据缺失、参数不对齐、中文元数据可接受、`ToolOutput` 保留 preview/detail 语义补充验证

## 4. Agent Runtime And Event Stream

- [x] 4.1 实现会话型 `Agent`，支持 `run(prompt)`、`stream(prompt)` 和 `reset()`
- [x] 4.2 建立内部 Strands runtime 适配层，把模型调用、工具调用和会话状态复用封装到 SDK 内部
- [x] 4.3 实现统一 `AgentEvent` 结构，覆盖 `thinking`、`tool`、`assistant`、`compress`、`system` 语义
- [x] 4.4 实现 thinking 与 tool 自动计时，并把时长注入事件流
- [x] 4.5 为多轮会话复用、流式 assistant 输出和事件时序补充验证

## 5. Conversation Compression

- [x] 5.1 实现默认事件化 `SummarizingConversationManager` 子类，并在 `Agent` 默认路径中接入
- [x] 5.2 在上下文压缩开始、完成、失败时复用统一事件机制发出 `compress_started`、`compress_completed`、`compress_failed`
- [x] 5.3 保留 reactive/proactive 压缩失败的原始控制流语义，同时确保失败事件可被上层消费
- [x] 5.4 支持开发者透传自定义 `conversation_manager`，并为可选 event sink 钩子预留接入点
- [x] 5.5 为默认压缩事件、自定义 manager 覆盖和压缩失败行为补充验证

## 6. Developer Experience

- [x] 6.1 编写最小 quickstart 文档，展示 `Agent`、`ModelConfig`、`tool`、`ToolOutput` 和 `agent.stream()` 的标准使用方式
- [x] 6.2 在文档中明确列出 v1 非目标：不提供 UI、环境变量系统、插件系统、多智能体 orchestration 或默认业务工具包
- [x] 6.3 复查整体 SDK 表面与实现结果，删除任何不属于五个公开名字范围的多余暴露项
