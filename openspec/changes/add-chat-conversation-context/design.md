## 设计目标

为 `ng chat` 补齐对话式 Agent 的“多轮上下文”基础设施，使其具备：

1. **可用的会话上下文记录**（不是仅定义变量）
2. **可闭环的澄清机制**（能消费澄清回答并继续执行）
3. **将历史用于意图识别**（指代消解、缺参补齐、范围沿用），同时保持安全边界与成本可控

## 核心原则

1. **当轮输入优先**：历史只能用于补全缺失信息，不得覆盖当轮的显式目标/范围/模式。
2. **成本可控**：历史必须裁剪（轮次/字符数/token 预算），禁止无上限增长。
3. **安全边界不降低**：破坏性操作与覆盖语义仍需显式确认，不引入“自然语言确认=自动执行”。
4. **优雅降级**：LLM 不可用时仍能运行（规则兜底 + 澄清），并保持“不静默扩张范围”的约束。

## 会话状态模型（建议）

- `ChatMessage`
  - `role`: user | assistant
  - `content`: str（裁剪前原文或裁剪后文本）
  - `created_at`: timestamp
  - `meta`: dict（可选：last_intent/last_scope/pending_tool/confirmation 等）
- `ConversationState`
  - `messages: list[ChatMessage]`
  - `summary: Optional[str]`（可选：长会话摘要）
  - `max_turns / max_chars / max_summary_chars`（来自配置）

裁剪策略（推荐）：

- 优先保留最近 `max_turns` 轮
- 同时保证总字符数不超过 `max_chars`
- 若仍超限：从最旧消息开始移除，并在可选启用时更新 `summary`

## 澄清闭环状态机

### 状态

- `Idle`：正常解析当轮输入
- `AwaitingClarification`：上一轮产生了 `ParsedIntent(needs_clarification=true)`，等待用户回答

### 转移（核心）

- `Idle -> AwaitingClarification`：
  - 规则/LLM 标记歧义，生成 1-3 个澄清问题与选项
  - 保存 `pending_clarification_intent`（包含 original_input、候选 target/mode/scope、questions/options）
- `AwaitingClarification -> Idle`：
  - 若用户回答能映射到选项（数字/关键词/同义表达）
  - 合并回 `pending_clarification_intent` 并进入“回显→确认→执行”
- `AwaitingClarification -> AwaitingClarification`：
  - 用户回答无法映射：重复提问（并提示可用的回答格式）
  - 超过次数上限：给出明确指令建议（如使用斜杠命令或补全范围）

## 意图识别链的历史注入

### 输入结构

对 LLM 意图识别链提供：

- `user_input`: 当轮输入
- `chat_history`: 最近 N 轮（role + content）
- `summary`: 可选摘要（长会话时提供）
- `project_context`（可选，不在本提案强制）：当前项目关键状态摘要（如已完成到哪一步）

### Prompt 约束（关键句式）

- 明确告知：当轮输入优先；历史只用于补全指代与缺参。
- 明确禁止：将历史中“曾经提到的范围”无确认地扩大/替换当轮明确范围。
- 对不确定情况：输出 `is_ambiguous=true` 并给出 `suggested_question`。

## 落盘策略（可选）

默认行为：仅内存保存，会话退出即丢失。

可选启用落盘：

- 目标文件：`projects/<project_id>/chat_history.jsonl`
- 约束：最大行数/最大文件大小；达到上限时滚动或截断
- 最小化：只存 role/content/ts，meta 仅存必要字段；对疑似敏感串（如 `OPENAI_API_KEY=`）做替换/脱敏

## 测试策略

重点覆盖：

1. 澄清闭环：问题→回答→执行计划生成
2. follow-up：范围沿用与不确定时的澄清
3. 裁剪：窗口上限与长文本输入
4. 兜底：LLM 失败/禁用时仍可工作，且不扩张范围

