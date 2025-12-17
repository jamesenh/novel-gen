## ADDED Requirements

### Requirement: Support Targeted Generation Requests with stop_at

The chat agent MUST distinguish between “全流程生成”与“目标型生成”，并在目标型生成中通过 `stop_at` 将工作流执行限制在目标节点及其必要前置范围内。

#### Scenario: Targeted generation request maps to a workflow stop node

- **WHEN** 用户输入 “生成人物角色”
- **THEN** 系统 MUST 识别目标产物为 “人物/角色”
- **AND** 系统 MUST 将该目标映射为工作流节点 `character_creation`
- **AND** 系统 MUST NOT 直接触发完整工作流执行到后续节点（如 `outline_creation`、章节生成等）

#### Scenario: Full-run intent remains explicit

- **WHEN** 用户输入 “开始生成/继续生成/一键生成/跑完整流程”（或等效表达）
- **THEN** 系统 MUST 将其识别为全流程生成意图
- **AND** 系统 MAY 选择 `workflow.run` 或 `workflow.resume`（根据项目状态）执行完整工作流

### Requirement: Ask Permission Before Backfilling Missing Prerequisites

当目标型生成所需前置数据缺失时，系统 MUST 先向用户说明将补齐哪些前置步骤，并在获得显式确认后才执行；用户拒绝则 MUST 不执行任何生成动作。

#### Scenario: Missing prerequisites triggers a scope confirmation prompt

- **WHEN** 用户请求 “生成人物角色”
- **AND** 系统通过 `workflow.status`（或等效）判断缺少 `world_creation` 或 `theme_conflict_creation`
- **THEN** 系统 MUST 复述计划：将补齐缺失前置，并在 `character_creation` 停止（`stop_at="character_creation"`）
- **AND** 系统 MUST 请求用户确认（例如提示 `/yes` 继续、`/no` 取消）
- **AND** 在用户确认前，系统 MUST NOT 开始执行生成相关工具

#### Scenario: Scope confirmation is not bypassed by /auto on

- **WHEN** 当前会话已启用 `/auto on`
- **AND** 用户触发目标型生成且需要补齐前置
- **THEN** 系统 MUST 仍然请求“补齐前置范围确认”
- **AND** 系统 MUST NOT 因 `/auto on` 而跳过该确认

#### Scenario: User declines prerequisite backfill

- **WHEN** 系统询问是否允许补齐前置
- **AND** 用户输入 `/no`
- **THEN** 系统 MUST 取消本次操作且不调用任何生成工具
- **AND** 系统 SHOULD 提供替代建议（例如先生成世界观/主题冲突，或使用斜杠命令分步执行）

### Requirement: Execute Targeted Generation and Stop at the Target Node

用户确认后，系统 MUST 执行目标型生成并在到达目标节点后停止，不再继续执行后续节点。

#### Scenario: Confirmed targeted generation stops at the requested node

- **WHEN** 用户确认补齐前置并继续执行目标型生成
- **THEN** 系统 MUST 调用工作流执行工具并设置 `stop_at="character_creation"`
- **AND** 系统 MUST 在 `character_creation` 节点完成后停止执行
- **AND** 系统 SHOULD 输出已生成产物摘要与下一步建议（例如“如需继续可使用 /run 或提示生成大纲”）

