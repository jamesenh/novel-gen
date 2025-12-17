## ADDED Requirements

### Requirement: Configure Chat Conversation Context Policy

The system MUST support configuring `ng chat` conversation context retention and intent-history injection behavior via environment variables and/or ProjectConfig.

#### Scenario: Configure history window limits

- **WHEN** 用户需要控制 chat 历史带来的 token/cost
- **THEN** 系统 MUST 支持配置项（环境变量或等效配置）：
  - `NOVELGEN_CHAT_HISTORY_MAX_TURNS`：最多保留最近 N 轮（默认建议 8-12）
  - `NOVELGEN_CHAT_HISTORY_MAX_CHARS`：历史总字符数上限（默认建议 8000-16000）

#### Scenario: Toggle history injection to LLM intent recognition

- **WHEN** 用户希望关闭“历史注入意图识别”（例如降低成本或排查行为）
- **THEN** 系统 MUST 支持配置项 `NOVELGEN_CHAT_INTENT_USE_HISTORY`（默认 true）

#### Scenario: Optional persistence of chat history

- **WHEN** 用户希望在会话退出后仍保留 chat 历史（调试/恢复）
- **THEN** 系统 MUST 支持配置项 `NOVELGEN_CHAT_HISTORY_PERSIST`（默认 false）
- **AND** 若启用，系统 MUST 具备最大长度/轮次限制并避免无界增长

