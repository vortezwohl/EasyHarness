# Verification Plan

## Metadata
- Document Type: Verification Plan
- Document ID: VERIFICATION
- Plan Name: canonical-stream-contract
- Created At: 2026-07-29:16:06:10.808
- Document Language: zh-CN

## Verification Matrix
| Area | Scenario | Required Assertion | Task |
| --- | --- | --- | --- |
| thinking | 两个 reasoning delta 后工具开始 | 两个 delta 原样一次出现，completed 无 delta，sequence 连续 | T-002, T-003 |
| assistant | 多个文本 delta 后 result | 不重放 result 全文，completed 无 delta | T-002, T-003 |
| assistant fallback | 无上游 delta 但有 result 文本 | 恰好一次合成 delta 后完成 | T-002, T-003 |
| lifecycle | 取消、失败、压缩 | 每个活动 phase 有唯一终态；failed 只用 error | T-002, T-003 |
| tools | 同名并发工具 | phase_id/工具 use ID 各自关联且终态正确 | T-002, T-003 |
| public surface | 类型与 README | 无旧字段、唯一消费方式、UTF-8 without BOM | T-001, T-003 |

## Commands
- `ruff check easyharness tests`
- `D:\github-project\EasyHarness\.venv\Scripts\python.exe -m unittest tests.test_sdk -v`
- 用 `rg` 搜索旧公开字段与版本兼容标记，并人工区分无关业务文本。

## Acceptance Gate
- 不接受仅“事件存在”的测试；必须验证完整顺序、字段组合、一次性文本和受保护行为。
