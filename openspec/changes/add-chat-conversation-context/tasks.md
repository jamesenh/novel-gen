## 1. Implementation

- [x] 1.1 设计并实现会话上下文模型（ChatMessage/ConversationState）：包含角色、内容、时间戳、可选结构化字段（last_intent/last_scope）
- [x] 1.2 在 `ChatAgent` 中接入会话记录：每轮写入 user/assistant 消息，并在执行计划/澄清时更新结构化元信息
- [x] 1.3 实现历史裁剪策略：最近 N 轮 + 最大字符数（配置化）；超过上限时按策略截断
- [x] 1.4 实现澄清闭环：保存 `pending_clarification` 的同时保存问题/选项；下一轮解析回答并合并回原意图，继续执行
- [x] 1.5 扩展 LLM 意图识别链输入：在 `parse_intent_by_llm()` 中纳入 `chat_history (+ optional summary)`；并更新 prompt 规则（当轮优先、历史补全）
- [x] 1.6 增加 follow-up 参数补全策略：当目标/范围缺失时，允许从最近一次"已确认/已执行"的意图中提取候选；不确定时走澄清
- [x] 1.7 增加可选落盘（默认关闭）：支持写入 `projects/<id>/chat_history.jsonl`，并实现长度上限与最小化/脱敏策略
- [x] 1.8 更新文档：补充澄清闭环与多轮 follow-up 示例，补充配置项说明

## 2. Validation

- [x] 2.1 单元测试：澄清闭环（"生成第3章"→追问→"2/正文"→正确路由到 chapter_text）
- [x] 2.2 单元测试：历史裁剪（轮次/字符数上限）与边界条件（空输入、极长输入）
- [x] 2.3 单元测试：follow-up 复用范围（上一轮 1-3 章计划完成 → "再生成正文" → 推断范围并回显确认）
- [x] 2.4 单元测试：LLM 失败/禁用时的行为（规则兜底 + 澄清；不扩张范围）
