## ADDED Requirements

### Requirement: Record Multi-turn Conversation Context in Session

The chat agent MUST record user/assistant messages in the current `ng chat` session and make them available for follow-up intent understanding and clarification closure.

#### Scenario: Record turns for follow-up

- **WHEN** 用户在同一会话内连续输入多轮自然语言
- **THEN** 系统 MUST 记录每轮的 `user` 与 `assistant` 消息（至少包含 role 与 content）
- **AND** 系统 MUST 支持按配置裁剪历史窗口（最近 N 轮/最大字符数），以限制成本与 token

### Requirement: Inject Chat History into LLM Intent Recognition

When LLM intent recognition is enabled, the system MUST provide recent chat history (and optional summary) alongside the current input to improve intent understanding for follow-ups and references.

#### Scenario: Use history to resolve references

- **GIVEN** 用户上一轮已明确指定范围 “前3章”
- **WHEN** 用户下一轮输入“再生成正文”（未显式范围）
- **THEN** 系统 MUST 使用对话历史推断候选范围并进行回显确认
- **AND** 若无法确定范围，系统 MUST 进入澄清而不是默认执行全量/全流程

### Requirement: Close the Clarification Loop Across Turns

If the system asks clarification questions, it MUST be able to consume the user's next-turn answers, merge them into the pending intent, and continue to plan/confirm/execute without requiring the user to restate the entire request.

#### Scenario: Clarify plan vs text and continue

- **WHEN** 用户输入“生成第3章”触发歧义澄清（计划 vs 正文）
- **THEN** 系统 MUST 保存待澄清意图与可选项
- **WHEN** 用户下一轮回复“2”（或“正文/章节正文”）
- **THEN** 系统 MUST 合并回答（mode=text）并继续进入“回显→确认→执行”流程

### Requirement: Preserve Safety Boundaries Under History-based Inference

History-based inference MUST NOT reduce confirmation requirements for destructive or overwriting operations.

#### Scenario: No implicit confirmation

- **WHEN** 上下文推断得到一个可执行计划
- **THEN** 系统 MUST 仍然遵循既有确认策略（例如生成/覆盖/回滚）
- **AND** 系统 MUST NOT 将“好/继续/可以”等自然语言视为 `/yes` 以执行破坏性操作

