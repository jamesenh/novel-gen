## ADDED Requirements

### Requirement: Provide CLI Chat Agent Entry Point

The system MUST provide a CLI entry point `ng chat <project_id>` that starts an interactive multi-turn session for a specific project.

#### Scenario: Start chat session and load context

- **WHEN** 用户运行 `ng chat demo_001`
- **THEN** 系统 MUST 加载项目目录下的当前状态（settings/world/outline/chapter_memory 等如存在）
- **AND** 系统 MUST 显示项目进度摘要（当前完成到哪一步、已生成到第几章）
- **AND** 系统 MUST 显示项目偏好摘要（如存在，Top N）

### Requirement: Support Slash Command Direct Tool Routing

The chat agent MUST route slash commands to deterministic tool calls without LLM decision-making.

#### Scenario: Slash command dispatch

- **WHEN** 用户输入 `/prefs`
- **THEN** 系统 MUST 调用 PreferenceTool.list 并打印项目偏好列表
- **AND** 系统 MUST 不调用 LLM 进行意图判断

### Requirement: Support Natural Language Intent Planning with ToolPlan

The chat agent MUST support natural language inputs by producing a structured tool execution plan (`ToolPlan`) and executing it through Tool Registry.

#### Scenario: Natural language triggers generation plan

- **WHEN** 用户输入 “继续生成到第 3 章”
- **THEN** 系统 MUST 解析意图为 Generate/Continue
- **AND** 若缺少项目状态或当前章节信息，系统 MUST 提问 1-3 个澄清问题
- **AND** 系统 MUST 生成结构化 ToolPlan（包含要调用的工具、参数、是否需要确认）
- **AND** ToolPlan 执行结果 MUST 被写回会话状态并用于下一轮对话

### Requirement: Perform Information Sufficiency Assessment and Tool-first Retrieval

The chat agent MUST assess whether information is sufficient before answering or executing, and MUST prefer tool-based retrieval to fill gaps before asking the user.

#### Scenario: Tool-first retrieval before asking user for missing info (generation)

- **WHEN** 用户输入自然语言请求生成/继续生成（如 “继续生成到第 3 章”）
- **THEN** 系统 MUST 先调用 WorkflowTool.status（或等效）以获取项目当前进度与可恢复状态
- **AND** 若仍缺少必要参数（如目标章节、是否 force、是否允许重算），系统 MUST 将缺失项列表化并提问 1-3 个澄清问题

#### Scenario: Tool-first retrieval before asking user for missing info (knowledge question)

- **WHEN** 用户提出人物/事件/关系类问题但缺少关键指代（如“他和师父关系什么时候变了？”）
- **THEN** 系统 MUST 先尝试调用 GraphTool（whois/relations/events 等）与/或 MemoryTool（scene/entity 检索）补全指代或候选列表
- **AND** 若工具结果存在多个候选（歧义），系统 MUST 向用户提问以确认目标（1-3 个问题）
- **AND** 系统 MUST 在最终回答中返回证据引用（至少章号与引用片段或 evidence_ref）

### Requirement: Enforce Retrieval Limits and Stop Conditions

The chat agent MUST enforce a bounded retrieval-and-clarification loop to avoid infinite tool calls.

#### Scenario: Bounded tool calls before clarification

- **WHEN** 系统判定信息不足
- **THEN** 系统 MUST 在询问用户前最多执行 N 次工具调用尝试补齐（N 默认 3，可配置）
- **AND** 若达到上限仍不足，系统 MUST 输出缺失信息清单并请求用户补充

#### Scenario: Stop when sufficient

- **WHEN** 系统已获得回答/执行所需的最小信息集
- **THEN** 系统 MUST 停止进一步检索与提问，并进入“复述计划并确认/直接回答”的阶段

### Requirement: Enforce Confirmation Policy with /auto Override

The chat agent MUST enforce a confirmation policy for generation actions by default, and MUST provide `/auto on|off` to toggle confirmation within the current session.

#### Scenario: Confirm generation by default

- **WHEN** 用户通过自然语言或 `/run` 触发生成（run/resume）
- **THEN** 系统 MUST 在执行前复述计划并请求确认

#### Scenario: Disable confirmation using /auto on

- **WHEN** 用户输入 `/auto on`
- **THEN** 系统 MUST 在当前会话内关闭 run/resume 的确认步骤
- **AND** 系统 MUST 仍然对回滚/清理/覆盖等破坏性动作保持确认


