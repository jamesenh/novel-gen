## ADDED Requirements

### Requirement: Use LLM-backed Intent Recognition for Natural Language

The chat agent MUST use an LLM-backed intent recognizer to parse natural language into a structured intent object, and MUST fall back to deterministic rules when LLM is unavailable.

#### Scenario: Slash commands bypass LLM

- **WHEN** 用户输入以 `/` 开头的斜杠命令（如 `/run`、`/status`）
- **THEN** 系统 MUST 直接按斜杠命令路由到工具
- **AND** 系统 MUST NOT 调用 LLM 进行意图识别

#### Scenario: LLM produces structured intent for scoped request

- **WHEN** 用户输入 “生成前3章的章节计划”
- **THEN** 系统 MUST 调用 LLM 意图识别器并产出结构化意图对象
- **AND** 结构化意图对象 MUST 包含：
  - 目标：章节计划
  - 范围：chapters=1..3
  - 是否需要澄清：false（在无歧义时）
- **AND** 系统 MUST 在执行前回显解析结果（目标与范围）

#### Scenario: LLM unavailable falls back to rules

- **WHEN** LLM 意图识别器不可用（例如 API Key 缺失、初始化失败、请求失败）
- **THEN** 系统 MUST 回退到规则/正则解析
- **AND** 若仍存在歧义或缺失关键参数，系统 MUST 提问澄清而不是扩张执行范围

### Requirement: Extract Structured Scope Constraints from Natural Language

The chat agent MUST extract and normalize scope constraints from natural language requests, especially for chapter-related intents.

#### Scenario: Parse “first N chapters” scope for chapter planning

- **WHEN** 用户输入 “生成前3章的章节计划”
- **THEN** 系统 MUST 识别目标为“章节计划（chapter planning）”
- **AND** 系统 MUST 解析范围约束为 `chapters=1..3`（或等价结构）
- **AND** 系统 MUST 在执行前回显解析结果（目标与范围）

#### Scenario: Parse chapter range scope

- **WHEN** 用户输入 “生成第2-5章的章节计划”（或“生成2到5章的章节计划”）
- **THEN** 系统 MUST 解析范围约束为 `chapters=2..5`
- **AND** MUST 保持边界包含性（2 与 5 均包含）

#### Scenario: Parse single chapter scope

- **WHEN** 用户输入 “生成第3章”
- **THEN** 系统 MUST 解析章节约束为 `chapter=3`
- **AND** 系统 MUST 将其标记为潜在歧义（章节计划 vs 章节正文），进入澄清流程

#### Scenario: Support Chinese numerals

- **WHEN** 用户输入包含中文数字（如“前三章”“第十章”“第十二章到第十五章”）
- **THEN** 系统 MUST 正确解析并标准化为阿拉伯数字范围/列表

### Requirement: Disambiguate Plan vs Text When Chapter Scope is Mentioned

When a request includes a chapter number but does not specify whether it refers to planning or text generation, the agent MUST ask a clarification question before executing.

#### Scenario: Clarify “generate chapter 3” intent

- **WHEN** 用户输入 “生成第3章”
- **THEN** 系统 MUST 询问用户选择：
  - 生成第3章的“章节计划”
  - 生成第3章的“章节正文”
- **AND** 在用户明确前，系统 MUST NOT 执行任何生成动作

### Requirement: Constraint-aware Fallback and No Silent Scope Expansion

If the agent can parse a scope constraint but cannot execute it precisely with available tools/workflow capabilities, it MUST not silently broaden the scope; it MUST ask the user to choose an acceptable alternative.

#### Scenario: Parsed constraint is unsupported by tooling

- **WHEN** 系统识别到请求 “生成前3章的章节计划”
- **AND** 当前工具/工作流不支持“仅对指定章节生成章节计划”
- **THEN** 系统 MUST 明确告知该限制
- **AND** 系统 MUST 提供可选方案（例如：生成全部章节计划、仅生成到 chapter_planning 阶段、或改用确定性命令）
- **AND** 在用户确认选项前，系统 MUST NOT 自动执行“默认全量章节计划”或“全流程生成”
